import datetime
import django.utils.timezone as timezone
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes, AttendanceMethodChoices
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector

User = get_user_model()


class TestDailyAttendanceSynthesisEngine(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Muhammed Analytics Labs")
        self.user = User.objects.create_user(username="jasil", email="jasil@labs.io")
        self.membership = Membership.objects.create(company=self.company, user=self.user, work_mode="office")
        self.target_date = datetime.date(2026, 6, 15)  # Enforce matching target date tracking matrices

    def test_ideal_present_shift_synthesis_calculation_flow(self):
        # Build balanced sequence punches pairs array matching standard work shifts
        base_datetime = datetime.datetime.combine(self.target_date, datetime.time(9, 0))
        timezone_aware_in = timezone.make_aware(base_datetime)
        timezone_aware_out = timezone.make_aware(base_datetime + datetime.timedelta(hours=9))

        AttendanceEvent.objects.create(company=self.company, membership=self.membership, event_type=AttendanceEventTypes.CHECK_IN, attendance_method=AttendanceMethodChoices.MANUAL, event_time=timezone_aware_in)
        AttendanceEvent.objects.create(company=self.company, membership=self.membership, event_type=AttendanceEventTypes.CHECK_OUT, attendance_method=AttendanceMethodChoices.MANUAL, event_time=timezone_aware_out)

        record = DailyAttendanceEngine.build_daily_attendance(company=self.company, membership=self.membership, target_date=self.target_date)

        self.assertEqual(record.attendance_status, DailyAttendanceStatus.PRESENT)
        self.assertEqual(record.total_work_minutes, 540)
        self.assertFalse(record.is_late)

    def test_incomplete_sequence_raises_review_required_flag(self):
        base_datetime = datetime.datetime.combine(self.target_date, datetime.time(9, 0))
        timezone_aware_in = timezone.make_aware(base_datetime)

        # Omit check-out log creation transaction block explicitly
        AttendanceEvent.objects.create(company=self.company, membership=self.membership, event_type=AttendanceEventTypes.CHECK_IN, attendance_method=AttendanceMethodChoices.MANUAL, event_time=timezone_aware_in)

        record = DailyAttendanceEngine.build_daily_attendance(company=self.company, membership=self.membership, target_date=self.target_date)

        self.assertEqual(record.attendance_status, DailyAttendanceStatus.INCOMPLETE)
        self.assertTrue(record.needs_review)

    def test_reprocessing_safely_recalculates_historical_records_payloads(self):
        base_datetime = datetime.datetime.combine(self.target_date, datetime.time(9, 0))
        timezone_aware_in = timezone.make_aware(base_datetime)
        AttendanceEvent.objects.create(company=self.company, membership=self.membership, event_type=AttendanceEventTypes.CHECK_IN, attendance_method=AttendanceMethodChoices.MANUAL, event_time=timezone_aware_in)

        # First cycle compilation generates incomplete flag summary sheet
        record_first = DailyAttendanceEngine.build_daily_attendance(company=self.company, membership=self.membership, target_date=self.target_date)
        self.assertTrue(record_first.needs_review)

        # HR retroactively logs missing checkout sequence punch mapping event reference block
        timezone_aware_out = timezone.make_aware(base_datetime + datetime.timedelta(hours=9))
        AttendanceEvent.objects.create(company=self.company, membership=self.membership, event_type=AttendanceEventTypes.CHECK_OUT, attendance_method=AttendanceMethodChoices.MANUAL, event_time=timezone_aware_out)

        # Invoke reprocessing engine to force structural normalization
        record_second = DailyAttendanceEngine.reprocess_attendance(company=self.company, membership=self.membership, target_date=self.target_date, actor=self.membership)

        self.assertEqual(record_second.attendance_status, DailyAttendanceStatus.PRESENT)
        self.assertFalse(record_second.needs_review)