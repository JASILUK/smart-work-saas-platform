import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector
from apps.attendance.selectors.face_enrollment_selector import FaceEnrollmentSelector
from apps.attendance.selectors.employee_shift_assignment_selectors import EmployeeShiftAssignmentSelector
from apps.attendance.selectors.company_work_schedule_selector import CompanyWorkScheduleSelector
from apps.attendance.selectors.holiday_selector import HolidaySelector
from apps.attendance.services.attendance_access_resolver_service import AttendanceAccessResolverService
from apps.attendance.services.live_attendance_service import LiveAttendanceService

User = get_user_model()

class EmployeeDashboardService:

    @staticmethod
    def get_dashboard(company, membership, today=None):
        if today is None:
            today = timezone.localtime(timezone.now()).date()

        # 1. Employee Context Definition
        employee_data = {
            "name": membership.user.get_full_name() or membership.user.username,
            "username": membership.user.username,
        }

        # 2. Shift Resolution Hierarchy Cascade
        current_shift = EmployeeShiftAssignmentSelector.get_active_assignment_for_date(
            membership=membership,
            date=today
        )
        if current_shift and getattr(current_shift, 'shift', None):
            shift_obj = current_shift.shift
            shift_data = {
                "name": shift_obj.name,
                "start": shift_obj.start_time.strftime("%H:%M:%S") if shift_obj.start_time else "",
                "end": shift_obj.end_time.strftime("%H:%M:%S") if shift_obj.end_time else "",
            }
        else:
            default_schedule = CompanyWorkScheduleSelector.get_by_company(company=company)
            if default_schedule and getattr(default_schedule, 'default_shift', None):
                shift_obj = default_schedule.default_shift
                shift_data = {
                    "name": shift_obj.name,
                    "start": shift_obj.start_time.strftime("%H:%M:%S") if shift_obj.start_time else "",
                    "end": shift_obj.end_time.strftime("%H:%M:%S") if shift_obj.end_time else "",
                }
            else:
                shift_data = None

        # 3. Present Activity State Aggregation
        live_status = LiveAttendanceService.get_member_status_for_date(
            membership=membership,
            date=today
        )
        
        daily_record = DailyAttendanceSelector.get_record_by_employee_and_date(
            membership=membership,
            date=today
        )
        
        working_minutes = 0
        check_in_time = ""
        check_out_time = ""
        
        if daily_record:
            working_minutes = getattr(daily_record, 'total_work_minutes', 0) or 0
        
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=today
        )
        if events:
            check_ins = [e for emp in [events] for e in (emp if isinstance(emp, list) else [emp]) if getattr(e, 'event_type', None) == 'CHECK_IN']
            check_outs = [e for emp in [events] for e in (emp if isinstance(emp, list) else [emp]) if getattr(e, 'event_type', None) == 'CHECK_OUT']
            
            if check_ins:
                sorted_ins = sorted(check_ins, key=lambda x: x.event_time)
                check_in_time = timezone.localtime(sorted_ins[0].event_time).strftime("%H:%M:%S")
            if check_outs:
                sorted_outs = sorted(check_outs, key=lambda x: x.event_time)
                check_out_time = timezone.localtime(sorted_outs[-1].event_time).strftime("%H:%M:%S")

        today_data = {
            "status": live_status or "NOT_CHECKED_IN",
            "check_in": check_in_time,
            "check_out": check_out_time,
            "working_minutes": working_minutes,
            "shift": shift_data,
        }

        # 4. Corrected Attendance Access Dictionary Resolution
        access_payload = AttendanceAccessResolverService.resolve_access(
            membership=membership,
            company=company
        )
        
        face_enrollment = FaceEnrollmentSelector.get_active_or_pending_enrollment(
            membership=membership,
            company=company
        )
        
        face_status = "NO_ENROLLMENT"
        if face_enrollment:
            face_status = getattr(face_enrollment, 'status', 'NO_ENROLLMENT')

        # ✅ FIXED: Treat access_payload explicitly as a dictionary payload
        allowed_methods = access_payload.get("methods", []) if access_payload else []
        validation_mode = access_payload.get("validation_mode", "ANY") if access_payload else "ANY"
        
        gps_required = False
        face_required = False
        is_biometric_hardware_only = "BIOMETRIC" in allowed_methods and len(allowed_methods) == 1

        if not is_biometric_hardware_only:
            # Under STRICT_ALL / ALL, every listed validation channel must satisfy requirements
            if validation_mode == "ALL":
                gps_required = "GPS" in allowed_methods
                face_required = "FACE" in allowed_methods
            else:
                # Under ANY mode, if there's only one method available, it becomes mandatory by default
                if len(allowed_methods) == 1:
                    gps_required = "GPS" in allowed_methods
                    face_required = "FACE" in allowed_methods
                else:
                    # If multiple methods are available in ANY mode, the user can choose. 
                    # We set flags to inform the frontend it has choices, but don't strictly lock either down as an absolute gate.
                    gps_required = False
                    face_required = False

        attendance_access_data = {
            "auto_synced": is_biometric_hardware_only,
            "primary_method": allowed_methods[0] if allowed_methods else None,
            "available_methods": allowed_methods,
            "validation_mode": validation_mode,
            "gps_required": gps_required,
            "face_required": face_required,
            "face_enrollment_status": face_status,
        }

        # 5. Core Action Strategy Matrix
        status = today_data["status"]
        actions_data = {
            "can_check_in": status == "NOT_CHECKED_IN",
            "can_check_out": status in ["CHECKED_IN", "ON_BREAK"],
            "can_start_break": status == "CHECKED_IN",
            "can_resume_break": status == "ON_BREAK",
        }

        # 6. Monthly Summaries Aggregator
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)

        monthly_records = DailyAttendanceSelector.get_records_for_date_range(
            membership=membership,
            start_date=start_of_month,
            end_date=end_of_month
        )

        present_days = 0
        late_days = 0
        absent_days = 0
        overtime_minutes = 0

        for record in monthly_records:
            rec_status = getattr(record, 'status', '')
            if rec_status == 'PRESENT' or getattr(record, 'total_work_minutes', 0) > 0:
                present_days += 1
            if getattr(record, 'is_late', False):
                late_days += 1
            if rec_status == 'ABSENT':
                absent_days += 1
            overtime_minutes += getattr(record, 'overtime_minutes', 0) or 0

        monthly_summary_data = {
            "present_days": present_days,
            "late_days": late_days,
            "absent_days": absent_days,
            "overtime_hours": round(overtime_minutes / 60, 2),
        }

        # 7. Core Extension Architecture Placeholders
        pending_requests_data = {
            "count": 0,
            "items": [],
        }

        leave_balance_data = {
            "enabled": False,
            "balances": [],
        }

        # 8. Upcoming Calendar Pipeline Events
        next_holiday_obj = HolidaySelector.get_next_upcoming_holiday(
            company=company,
            from_date=today
        )
        next_holiday_data = None
        if next_holiday_obj:
            next_holiday_data = {
                "name": next_holiday_obj.name,
                "date": next_holiday_obj.holiday_date.strftime("%Y-%m-%d"),
                "is_paid": next_holiday_obj.is_paid,
            }

        next_assignment = EmployeeShiftAssignmentSelector.get_next_upcoming_assignment(
            membership=membership,
            from_date=today
        )
        next_shift_data = None
        if next_assignment and getattr(next_assignment, 'shift', None):
            next_shift_obj = next_assignment.shift
            next_shift_data = {
                "name": next_shift_obj.name,
                "start": next_shift_obj.start_time.strftime("%H:%M:%S") if next_shift_obj.start_time else "",
                "end": next_shift_obj.end_time.strftime("%H:%M:%S") if next_shift_obj.end_time else "",
                "effective_from": next_assignment.effective_from.strftime("%Y-%m-%d"),
            }

        upcoming_data = {
            "next_holiday": next_holiday_data,
            "next_shift": next_shift_data,
        }

        return {
            "employee": employee_data,
            "today": today_data,
            "attendance_access": attendance_access_data,
            "actions": actions_data,
            "monthly_summary": monthly_summary_data,
            "pending_requests": pending_requests_data,
            "leave_balance": leave_balance_data,
            "upcoming": upcoming_data,
        }