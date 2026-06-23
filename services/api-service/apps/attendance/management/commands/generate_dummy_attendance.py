import random
import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes, AttendanceMethodChoices


def make_aware(dt, tz):
    """Make naive datetime aware using Django's make_aware (works with pytz and zoneinfo)."""
    from django.utils.timezone import is_naive, make_aware as django_make_aware
    if is_naive(dt):
        return django_make_aware(dt, timezone=tz)
    return dt


class Command(BaseCommand):
    help = "Generate dummy DailyAttendance and AttendanceEvent records for testing"

    def add_arguments(self, parser):
        parser.add_argument("--membership", type=int, required=True, help="Membership ID")
        parser.add_argument("--days", type=int, default=30, help="Number of days")
        parser.add_argument("--company", type=int, default=4, help="Company ID")
        parser.add_argument("--clear", action="store_true", help="Clear existing first")

    @transaction.atomic
    def handle(self, *args, **options):
        membership_id = options["membership"]
        company_id = options["company"]
        days = options["days"]
        clear = options["clear"]

        try:
            membership = Membership.objects.get(id=membership_id)
            company = Company.objects.get(id=company_id)
        except Membership.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Membership {membership_id} not found"))
            return
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Company {company_id} not found"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Generating {days} days for {membership.user.username} (membership {membership_id})"
        ))

        if clear:
            deleted_daily = DailyAttendance.objects.filter(membership=membership).delete()
            deleted_events = AttendanceEvent.objects.filter(membership=membership).delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared: {deleted_daily[0]} DailyAttendance, {deleted_events[0]} AttendanceEvent"
            ))

        today = timezone.localtime(timezone.now()).date()
        records_created = 0
        events_created = 0

        for day_offset in range(days - 1, -1, -1):
            target_date = today - datetime.timedelta(days=day_offset)

            # Weekend: Saturday=5, Sunday=6
            if target_date.weekday() in [5, 6]:
                DailyAttendance.objects.create(
                    company=company,
                    membership=membership,
                    attendance_date=target_date,
                    attendance_status="WEEKEND",
                    is_weekend=True,
                    total_work_minutes=0,
                    required_work_minutes=0,
                )
                records_created += 1
                continue

            # Random status distribution:
            # 5% LEAVE, 10% ABSENT, 25% LATE (of remaining 85%), 60% NORMAL PRESENT
            rand = random.random()
            
            if rand < 0.05:
                # LEAVE
                DailyAttendance.objects.create(
                    company=company,
                    membership=membership,
                    attendance_date=target_date,
                    attendance_status="LEAVE",
                    is_leave=True,
                    total_work_minutes=0,
                    required_work_minutes=480,
                )
                records_created += 1
                continue

            elif rand < 0.15:
                # ABSENT
                DailyAttendance.objects.create(
                    company=company,
                    membership=membership,
                    attendance_date=target_date,
                    attendance_status="ABSENT",
                    is_absent=True,
                    total_work_minutes=0,
                    required_work_minutes=480,
                )
                records_created += 1
                continue

            # PRESENT day (85% of days) — now split into late vs normal
            # Late: 25% of present days = ~21% total
            # Normal: 75% of present days = ~64% total
            is_late = random.random() < 0.30  # 30% of present days are late

            # Night shift: 22:00 -> 06:00
            shift_start_hour = 22
            shift_start_min = 0

            if is_late:
                # Late arrival: 22:15 to 22:45
                check_in_hour = 22
                check_in_min = random.randint(15, 45)
                late_minutes = (check_in_hour - shift_start_hour) * 60 + (check_in_min - shift_start_min)
            else:
                # Normal/early arrival: 21:45 to 21:59
                check_in_hour = 21
                check_in_min = random.randint(45, 59)
                late_minutes = 0

            # Check-out: 05:00 to 06:30 (some stay late, some leave early)
            check_out_hour = random.choice([5, 6])
            check_out_min = random.randint(0, 30)

            # Break: 01:00 to 02:30
            break_out_hour = 1
            break_out_min = random.randint(0, 15)
            break_in_hour = 2
            break_in_min = random.randint(0, 30)

            # Calculate work minutes
            check_in_naive = datetime.datetime.combine(target_date, datetime.time(check_in_hour, check_in_min))
            check_out_naive = datetime.datetime.combine(target_date + datetime.timedelta(days=1), datetime.time(check_out_hour, check_out_min))
            total_seconds = (check_out_naive - check_in_naive).total_seconds()
            
            break_out_naive = datetime.datetime.combine(target_date + datetime.timedelta(days=1), datetime.time(break_out_hour, break_out_min))
            break_in_naive = datetime.datetime.combine(target_date + datetime.timedelta(days=1), datetime.time(break_in_hour, break_in_min))
            break_seconds = (break_in_naive - break_out_naive).total_seconds()

            work_minutes = max(0, int((total_seconds - break_seconds) / 60))

            # Timezone-aware datetimes for DailyAttendance
            default_tz = timezone.get_default_timezone()
            first_check_in = make_aware(check_in_naive, default_tz)
            last_check_out = make_aware(check_out_naive, default_tz)

            # Create DailyAttendance
            daily = DailyAttendance.objects.create(
                company=company,
                membership=membership,
                attendance_date=target_date,
                attendance_status="PRESENT",
                first_check_in_at=first_check_in,
                last_check_out_at=last_check_out,
                total_work_minutes=work_minutes,
                total_break_minutes=int(break_seconds / 60),
                required_work_minutes=480,
                late_minutes=late_minutes,
                is_late=is_late,
                is_half_day=work_minutes < 240,
                source="SYSTEM",
            )
            records_created += 1

            # Create AttendanceEvents (same datetimes, timezone-aware)
            event_check_in = make_aware(check_in_naive, default_tz)
            event_break_out = make_aware(break_out_naive, default_tz)
            event_break_in = make_aware(break_in_naive, default_tz)
            event_check_out = make_aware(check_out_naive, default_tz)

            # CHECK_IN event
            AttendanceEvent.objects.create(
                company=company,
                membership=membership,
                event_type=AttendanceEventTypes.CHECK_IN,
                attendance_method=AttendanceMethodChoices.GPS_FACE,
                event_time=event_check_in,
                verification_payload={"gps": {"verified": True}, "face": {"confidence": 0.95}},
                created_by=membership,
            )
            events_created += 1

            # BREAK_OUT event
            AttendanceEvent.objects.create(
                company=company,
                membership=membership,
                event_type=AttendanceEventTypes.BREAK_OUT,
                attendance_method=AttendanceMethodChoices.GPS_FACE,
                event_time=event_break_out,
                verification_payload={"gps": {"verified": True}},
                created_by=membership,
            )
            events_created += 1

            # BREAK_IN event
            AttendanceEvent.objects.create(
                company=company,
                membership=membership,
                event_type=AttendanceEventTypes.BREAK_IN,
                attendance_method=AttendanceMethodChoices.GPS_FACE,
                event_time=event_break_in,
                verification_payload={"gps": {"verified": True}},
                created_by=membership,
            )
            events_created += 1

            # CHECK_OUT event
            AttendanceEvent.objects.create(
                company=company,
                membership=membership,
                event_type=AttendanceEventTypes.CHECK_OUT,
                attendance_method=AttendanceMethodChoices.GPS_FACE,
                event_time=event_check_out,
                verification_payload={"gps": {"verified": True}, "face": {"confidence": 0.92}},
                created_by=membership,
            )
            events_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {records_created} DailyAttendance and {events_created} AttendanceEvent records."
        ))