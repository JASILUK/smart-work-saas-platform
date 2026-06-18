from django.test import TestCase
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice, BiometricSyncMode, BiometricDeviceBrand
from apps.attendance.models.biometric_employee_mapping import BiometricEmployeeMapping
from apps.attendance.services.biometric_device_service import BiometricDeviceService
from apps.attendance.services.biometric_employee_mapping_service import BiometricEmployeeMappingService

User = get_user_model()

class TestBiometricInfrastructureSystem(TestCase):
    def setUp(self):
        # Build independent tenant boundaries contexts structures
        self.company_alpha = Company.objects.create(name="Alpha Holdings")
        self.company_beta = Company.objects.create(name="Beta Industries")

        self.user_1 = User.objects.create_user(username="muhammed", email="m@alpha.internal")
        self.user_2 = User.objects.create_user(username="jasil", email="j@beta.internal")

        self.member_alpha = Membership.objects.create(company=self.company_alpha, user=self.user_1)
        self.member_beta = Membership.objects.create(company=self.company_beta, user=self.user_2)

    def test_create_pull_device_with_networking_succeeds(self):
        device = BiometricDeviceService.create_device(
            company=self.company_alpha,
            validated_data={
                "name": "Main Gate Terminal",
                "device_code": "ALPHA-GATE-01",
                "brand": BiometricDeviceBrand.ZKTECO,
                "sync_mode": BiometricSyncMode.PULL,
                "ip_address": "192.168.1.50",
                "port": 4370
            }
        )
        self.assertEqual(device.device_code, "ALPHA-GATE-01")
        self.assertTrue(device.is_active)

    def test_pull_device_without_ip_address_fails_validation(self):
        with self.assertRaises(DjangoValidationError):
            BiometricDeviceService.create_device(
                company=self.company_alpha,
                validated_data={
                    "name": "Failing Gate Terminal",
                    "device_code": "ALPHA-FAIL",
                    "brand": BiometricDeviceBrand.ESSL,
                    "sync_mode": BiometricSyncMode.PULL,
                    "ip_address": None,
                    "port": 4370
                }
            )

    def test_push_device_without_ip_address_succeeds(self):
        device = BiometricDeviceService.create_device(
            company=self.company_alpha,
            validated_data={
                "name": "Cloud Push Terminal",
                "device_code": "ALPHA-PUSH-01",
                "brand": BiometricDeviceBrand.HIKVISION,
                "sync_mode": BiometricSyncMode.PUSH,
                "ip_address": None,
                "port": 8000
            }
        )
        self.assertEqual(device.sync_mode, BiometricSyncMode.PUSH)

    def test_duplicate_device_codes_blocked_by_constraints(self):
        BiometricDeviceService.create_device(
            company=self.company_alpha,
            validated_data={"name": "Gate A", "device_code": "GATE-01", "sync_mode": BiometricSyncMode.MANUAL}
        )
        with self.assertRaises(Exception):  # Unique constraint DB integrity block check triggered
            BiometricDevice.objects.create(
                company=self.company_alpha,
                name="Gate B",
                device_code="GATE-01",
                sync_mode=BiometricSyncMode.MANUAL
            )

    def test_device_lifecycle_soft_deactivation_loops(self):
        device = BiometricDevice.objects.create(company=self.company_alpha, name="Temp", device_code="T-01")
        BiometricDeviceService.deactivate_device(device=device)
        self.assertFalse(device.is_active)
        BiometricDeviceService.activate_device(device=device)
        self.assertTrue(device.is_active)

    def test_create_valid_employee_biometric_mapping(self):
        device = BiometricDevice.objects.create(company=self.company_alpha, name="Gate A", device_code="G-A")
        mapping = BiometricEmployeeMappingService.create_mapping(
            company=self.company_alpha,
            actor=self.member_alpha,
            validated_data={
                "membership": self.member_alpha,
                "device": device,
                "device_user_id": "102"
            }
        )
        self.assertEqual(mapping.device_user_id, "102")
        self.assertTrue(mapping.is_active)

    def test_duplicate_employee_on_same_device_blocked(self):
        device = BiometricDevice.objects.create(company=self.company_alpha, name="Gate A", device_code="G-A")
        BiometricEmployeeMapping.objects.create(company=self.company_alpha, membership=self.member_alpha, device=device, device_user_id="102")
        
        with self.assertRaises(Exception):
            BiometricEmployeeMapping.objects.create(company=self.company_alpha, membership=self.member_alpha, device=device, device_user_id="505")

    def test_duplicate_device_user_id_on_same_device_blocked(self):
        device = BiometricDevice.objects.create(company=self.company_alpha, name="Gate A", device_code="G-A")
        BiometricEmployeeMapping.objects.create(company=self.company_alpha, membership=self.member_alpha, device=device, device_user_id="102")
        
        # Initialize second user partition target trying to use matching hardware slots mapping indices tags
        user_backup = User.objects.create_user(username="backup_worker", email="b@alpha.internal")
        member_backup = Membership.objects.create(company=self.company_alpha, user=user_backup)
        
        with self.assertRaises(Exception):
            BiometricEmployeeMapping.objects.create(company=self.company_alpha, membership=member_backup, device=device, device_user_id="102")

    def test_cross_company_tenant_mapping_restricted_explicitly(self):
        # Hardware terminal located in Company Alpha's network boundary
        device_alpha = BiometricDevice.objects.create(company=self.company_alpha, name="Alpha Perimeter", device_code="A-PER")
        
        # Attempt to map an employee working for Company Beta into Alpha's hardware unit context
        with self.assertRaises(DjangoValidationError):
            BiometricEmployeeMappingService.create_mapping(
                company=self.company_beta,
                actor=self.member_beta,
                validated_data={
                    "membership": self.member_beta, # Company Beta
                    "device": device_alpha,         # Company Alpha
                    "device_user_id": "777"
                }
            )