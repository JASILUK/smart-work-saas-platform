from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes, AttendanceMethodChoices
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault, ValidationModeChoices
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.services.check_in_service import CheckInService
from apps.attendance.services.check_out_service import CheckOutService
from apps.attendance.services.live_attendance_service import LiveAttendanceService

User = get_user_model()

class TestAttendanceEventWorkflowEngine(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Central Engineering Labs")
        self.user = User.objects.create_user(username="faisal", email="faisal@labs.io")
        self.membership = Membership.objects.create(company=self.company, user=self.user, work_mode="office")
        
        # Deploy access constraints defaults
        self.cmethod = CompanyAttendanceMethod.objects.create(company=self.company, method="GPS", is_active=True)
        self.location = AttendanceLocation.objects.create(
            company=self.company, name="HQ Tower", latitude=8.524100, longitude=76.936600, radius_meters=100, is_active=True
        )
        self.adefault = CompanyAttendanceDefault.objects.create(company=self.company, validation_mode=ValidationModeChoices.ANY, is_active=True)
        self.adefault.allowed_methods.add(self.cmethod)
        self.adefault.allowed_locations.add(self.location)

    def test_valid_check_in_within_geofence_perimeter_succeeds(self):
        event = CheckInService.check_in(
            company=self.company, membership=self.membership,
            method=AttendanceMethodChoices.GPS_ONLY,
            evidence={"latitude": 8.524102, "longitude": 76.936601},
            actor=self.membership
        )
        self.assertEqual(event.event_type, AttendanceEventTypes.CHECK_IN)
        self.assertEqual(event.location_id, self.location.id)
        self.assertEqual(LiveAttendanceService.get_member_status(company=self.company, membership=self.membership), "PRESENT")

    def test_check_in_outside_geofence_perimeter_fails_validation(self):
        with self.assertRaises(DjangoValidationError):
            CheckInService.check_in(
                company=self.company, membership=self.membership,
                method=AttendanceMethodChoices.GPS_ONLY,
                evidence={"latitude": 11.250000, "longitude": 75.780000}, # Far away coordinates
                actor=self.membership
            )

    def test_redundant_double_check_in_actions_are_blocked(self):
        evidence_payload = {"latitude": 8.524102, "longitude": 76.936601}
        CheckInService.check_in(company=self.company, membership=self.membership, method=AttendanceMethodChoices.GPS_ONLY, evidence=evidence_payload, actor=self.membership)
        
        with self.assertRaises(DjangoValidationError):
            CheckInService.check_in(company=self.company, membership=self.membership, method=AttendanceMethodChoices.GPS_ONLY, evidence=evidence_payload, actor=self.membership)

    def test_checkout_before_checking_in_fails_validation(self):
        with self.assertRaises(DjangoValidationError):
            CheckOutService.check_out(
                company=self.company, membership=self.membership,
                method=AttendanceMethodChoices.GPS_ONLY,
                evidence={"latitude": 8.524102, "longitude": 76.936601},
                actor=self.membership
            )