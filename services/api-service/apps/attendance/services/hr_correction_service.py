# apps/attendance/services/hr_correction_service.py
"""
HR System Attendance Correction Service Layer

Orchestrates atomic adjustments to transactional event logs. Handles rollback boundaries,
injects audit traces into json payloads, and re-triggers downstream summaries.
"""

import datetime
import zoneinfo
from typing import Any
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes, AttendanceMethodChoices
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector
from apps.attendance.validators.timeline_validator import TimelineSequenceValidator
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine


class HRAttendanceCorrectionService:
    """
    Monitors, alters, and recalculates timesheet sequences securely.
    """

    @classmethod
    def process_event_correction(
        cls,
        *,
        company: Company,
        operator: Membership,
        membership_id: int,
        target_date: datetime.date,
        event_id: int = None,
        event_type: str = None,
        event_time: Any,
        notes: str = ""
    ) -> AttendanceEvent:
        """
        Executes a complete, safe transaction cycle to mutate or append clock logs.
        """
        target_employee = Membership.objects.filter(id=membership_id, company=company, is_active=True).first()
        if not target_employee:
            raise ValidationError({"membership_id": ["Target employee was not found within this active workspace."]})

        # ─── FIXED: PARSE AS DIRECT UTC TO PREVENT TIMEZONE DRIFT ─────────────
        if isinstance(event_time, str):
            if "T" in event_time:
                event_time = event_time.replace("T", " ")
            
            clean_time_str = event_time.split(".")[0]
            if len(clean_time_str) == 16:  # YYYY-MM-DD HH:MM
                naive_datetime = datetime.datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M")
            else:
                naive_datetime = datetime.datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M:%S")
                
            # Treat the incoming picker time string directly as UTC time 
            event_time_utc = timezone.make_aware(naive_datetime, timezone.utc)
        else:
            if timezone.is_naive(event_time):
                event_time_utc = timezone.make_aware(event_time, timezone.utc)
            else:
                event_time_utc = event_time.astimezone(timezone.utc)
        # ───────────────────────────────────────────────────────────────────────

        with transaction.atomic():
            # 1. Fetch existing sequence tracking blocks for the target day
            db_events = list(AttendanceEventSelector.get_events_for_membership_and_date(
                membership=target_employee, 
                date=target_date
            ))

            # 2. Extract or construct the operational entity node instance
            if event_id:
                target_event = AttendanceEventSelector.get_by_id(event_id=event_id, company=company)
                if not target_event or target_event.membership != target_employee:
                    raise ValidationError({"event_id": ["Target event record trace was not found within this context scope."]})
            else:
                if not event_type:
                    raise ValidationError({"event_type": ["An explicit event type mapping is required for inserts."]})
                if event_type not in AttendanceEventTypes.values:
                    raise ValidationError({"event_type": ["Invalid system transactional event code mapping provided."]})
                
                target_event = AttendanceEvent(
                    company=company,
                    membership=target_employee,
                    event_type=event_type,
                    attendance_method=AttendanceMethodChoices.MANUAL,
                    is_system_generated=False
                )

            # 3. Simulate timeline array to calculate edge exceptions before save triggers
            simulated_list = []
            replaced = False

            for ev in db_events:
                if event_id and ev.id == event_id:
                    simulated_list.append({
                        "id": ev.id,
                        "event_type": ev.event_type,
                        "event_time": event_time_utc
                    })
                    replaced = True
                else:
                    simulated_list.append({
                        "id": ev.id,
                        "event_type": ev.event_type,
                        "event_time": ev.event_time
                    })

            if not replaced:
                simulated_list.append({
                    "id": None,
                    "event_type": event_type if not event_id else target_event.event_type,
                    "event_time": event_time_utc
                })

            # ─── FIXED: SHIFT-AWARE SIMULATION SORT MATRIX ──────────────────────────
            TYPE_WEIGHTS = {
                AttendanceEventTypes.CHECK_IN: 1,
                AttendanceEventTypes.BREAK_OUT: 2,
                AttendanceEventTypes.BREAK_IN: 3,
                AttendanceEventTypes.CHECK_OUT: 4,
            }

            # Extract check ins to check for night-shift status anchoring
            check_ins = [e for e in simulated_list if e["event_type"] == AttendanceEventTypes.CHECK_IN]
            
            def get_simulation_sort_key(item):
                t = item["event_time"]
                if check_ins:
                    # If the shift starts late at night (past 18:00 / 6 PM), early morning events
                    # (00:00 to 12:00) belong at the end of the timeline sequence loop (+24 hour weight shift)
                    primary_in_time = check_ins[0]["event_time"]
                    if primary_in_time.hour >= 18 and t.hour < 18:
                        return (1, t.date(), TYPE_WEIGHTS.get(item["event_type"], 0), t)
                
                return (0, t.date(), TYPE_WEIGHTS.get(item["event_type"], 0), t)

            simulated_list.sort(key=get_simulation_sort_key)
            # ───────────────────────────────────────────────────────────────────────

            # 4. Enforce structural validation pass rules
            is_valid, sequence_errors = TimelineSequenceValidator.validate_timeline(simulated_list)
            if not is_valid:
                raise ValidationError(detail=sequence_errors)

            # 5. Build native JSON data logging track trace details
            if event_id:
                old_time_iso = target_event.event_time.isoformat()
                new_time_iso = event_time_utc.isoformat()
                
                audit_snapshot = target_event.verification_payload.get("hr_correction_audit", [])
                audit_snapshot.append({
                    "changed_by_id": operator.id,
                    "changed_at": timezone.now().isoformat(),
                    "field": "event_time",
                    "original_value": old_time_iso,
                    "new_value": new_time_iso,
                    "reason": notes
                })
                target_event.verification_payload["hr_correction_audit"] = audit_snapshot

            # Bind values onto instance fields
            target_event.event_time = event_time_utc
            target_event.notes = notes
            target_event.created_by = operator
            target_event.save()

            # 6. Re-execute the tracking engine framework to automatically align summary metrics
            DailyAttendanceEngine.build_daily_attendance(
                company=company,
                membership=target_employee,
                target_date=target_date
            )

            return target_event