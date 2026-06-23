# Create the management command directory structure
mkdir -p apps/attendance/management/commands

# Create the command file
cat > apps/attendance/management/commands/generate_dummy_attendance.py << 'PYEOF'
import random
import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes, AttendanceMethodChoices


class Command(BaseCommand):
    help = "Generate dummy DailyAttendance and AttendanceEvent records for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--membership",
            type=int,
            required=True,
            help="Membership ID to generate data for",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to generate (default: 30)",
        )
        parser.add_argument(
            "--company",
            type=int,
            default=4,
            help="Company ID (default: 4)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing records for this membership first",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        membership_id = options["membership"]
        company_id = options["company"]
        days = options["days"]
        clear = options["clear"]

        # Get membership and company
        try:
            membership = Membership.objects.get(id=membership_id)
            company = Company.objects.get(id=company_id)
        except Membership.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Membership {membership_id} not found"))
            return
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Company {company_id} not found"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Generating {days} days of dummy data for {membership.user.username} (membership {membership_id})"
            )
        )

        # Clear existing data if requested
        if clear:
            deleted_daily = DailyAttendance.objects.filter(membership=membership).delete()
            deleted_events = AttendanceEvent.objects.filter(membership=membership).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared: {deleted_daily[0]} DailyAttendance, {deleted_events[0]} AttendanceEvent"
                )
            )

        # Generate data for last N days
        today = timezone.localtime(timezone.now()).date()
        records_created = 0
        events_created = 0

        for day_offset in range(days - 1, -1, -1):
            target_date = today - datetime.timedelta(days=day_offset)

            # Skip weekends (Saturday=5, Sunday=6)
            if target_date.weekday() in [5, 6]:
                # Create weekend record
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

            # Random status: 70% present, 15% absent, 10% late, 5% leave
            rand = random.random()
            
            if rand < 0.05:
                # Leave
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
                # Absent
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

            # Present or Late - generate events
            is_late = rand < 0.25  # 25% of present days are late
            
            # Shift: 22:00 to 06:00 (night shift)
            shift_start = datetime.time(22, 0)
            shift_end = datetime.time(6, 0)

            # Check-in time (with variation)
            if is_late:
                check_in_time = datetime.time(22, random.randint(15, 45))  # 22:15 to 22:45
                late_minutes = (check_in_time.hour - shift_start.hour) * 60 + (check_in_time.minute - shift_start.minute)
            else:
                check_in_time = datetime.time(21, random.randint(45, 59))  # 21:45 to 21:59 (early)
                late_minutes = 0

            # Check-out time
            check_out_time = datetime.time(random.randint(5, 7), random.randint(0, 30))

            # Break time
            break_out_time = datetime.time(1, random.randint(0, 10))
            break_in_time = datetime.time(2, random.randint(0, 10))

            # Calculate work minutes
            check_in_dt = datetime.datetime.combine(target_date, check_in_time)
            check_out_dt = datetime.datetime.combine(target_date + datetime.timedelta(days=1), check_out_time)
            total_seconds = (check_out_dt - check_in_dt).total_seconds()
            
            break_out_dt = datetime.datetime.combine(target_date + datetime.timedelta(days=1), break_out_time)
            break_in_dt = datetime.datetime.combine(target_date + datetime.timedelta(days=1), break_in_time)
            break_seconds = (break_in_dt - break_out_dt).total_seconds()

            work_minutes = max(0, int((total_seconds - break_seconds) / 60))

            # Create DailyAttendance
            daily = DailyAttendance.objects.create(
                company=company,
                membership=membership,
                attendance_date=target_date,
                attendance_status="PRESENT",
                first_check_in_at=check_in_time,
                last_check_out_at=check_out_time,
                total_work_minutes=work_minutes,
                total_break_minutes=int(break_seconds / 60),
                required_work_minutes=480,
                late_minutes=late_minutes,
                is_late=is_late,
                is_half_day=work_minutes < 240,
                source="SYSTEM",
            )
            records_created += 1

            # Create AttendanceEvents
            naive_check_in = datetime.datetime.combine(target_date, check_in_time)
            naive_check_out = datetime.datetime.combine(target_date + datetime.timedelta(days=1), check_out_time)
            naive_break_out = datetime.datetime.combine(target_date + datetime.timedelta(days=1), break_out_time)
            naive_break_in = datetime.datetime.combine(target_date + datetime.timedelta(days=1), break_in_time)

            company_tz = timezone.get_default_timezone()
            check_in_dt = company_tz.localize(naive_check_in)
            check_out_dt = company_tz.localize(naive_check_out)
            break_out_dt = company_tz.localize(naive_break_out)
            break_in_dt = company_tz.localize(naive_break_in)

            # CHECK_IN event
            AttendanceEvent.objects.create(
                company=company,
                membership=membership,
                event_type=AttendanceEventTypes.CHECK_IN,
                attendance_method=AttendanceMethodChoices.GPS_FACE,
                event_time=check_in_dt,
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
                event_time=break_out_dt,
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
                event_time=break_in_dt,
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
                event_time=check_out_dt,
                verification_payload={"gps": {"verified": True}, "face": {"confidence": 0.92}},
                created_by=membership,
            )
            events_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created {records_created} DailyAttendance records and {events_created} AttendanceEvent records."
            )
        )
PYEOF

# Create __init__.py files
touch apps/attendance/management/__init__.py
touch apps/attendance/management/commands/__init__.py

echo "=========================================="
echo "Command created successfully!"
echo "=========================================="
echo ""
echo "Run with:"
echo "  docker compose exec api python manage.py generate_dummy_attendance --membership 2 --days 30"
echo ""
echo "Options:"
echo "  --membership 2    # Membership ID (required)"
echo "  --company 4       # Company ID (default: 4)"
echo "  --days 30         # Number of days (default: 30)"
echo "  --clear           # Clear existing data first"
echo ""
echo "Examples:"
echo "  # Generate 30 days for jasil (membership 2)"
echo "  docker compose exec api python manage.py generate_dummy_attendance --membership 2 --days 30"
echo ""
echo "  # Clear and regenerate"
echo "  docker compose exec api python manage.py generate_dummy_attendance --membership 2 --clear --days 60"
echo ""
echo "  # Generate for Ajal (membership 4)"
echo "  docker compose exec api python manage.py generate_dummy_attendance --membership 4 --days 30"
echo "=========================================="