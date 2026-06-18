import uuid
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice, BiometricSyncMode
from apps.attendance.models.biometric_log import BiometricLog, ProcessingStatusChoices
from apps.attendance.models.biometric_employee_mapping import BiometricEmployeeMapping
from apps.attendance.services.biometric_log_service import BiometricLogService
from apps.attendance.services.biometric_pull_ingestion_service import BiometricPullIngestionService

User = get_user_model()

class TestBiometricLogSyncSystem(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Muhammed Dev Labs")
        self.user = User.objects.create_user(username="jasil", email="jasil@labs.io")
        self.membership = Membership.objects.create(company=self.company, user=self.user)
        
        self.device = BiometricDevice.objects.create(
            company=self.company, name="Front Gate", device_code="FG-01", sync_mode=BiometricSyncMode.PULL
        )
        self.mapping = BiometricEmployeeMapping.objects.create(
            company=self.company, membership=self.membership, device=self.device, device_user_id="102"
        )

    def test_create_log_maps_employee_successfully(self):
        log = BiometricLogService.create_log(
            company=self.company,
            validated_data={
                "device": self.device,
                "device_user_id": "102",
                "punch_time": timezone.now(),
                "source": "PULL",
                "device_log_id": "TX_999"
            }
        )
        self.assertEqual(log.membership_id, self.membership.id)
        self.assertEqual(log.processing_status, ProcessingStatusChoices.PENDING)

    def test_duplicate_device_log_id_returns_existing_record(self):
        time_mark = timezone.now()
        log_first = BiometricLogService.create_log(
            company=self.company,
            validated_data={"device": self.device, "device_user_id": "102", "punch_time": time_mark, "source": "PULL", "device_log_id": "DUP_ID"}
        )
        log_second = BiometricLogService.create_log(
            company=self.company,
            validated_data={"device": self.device, "device_user_id": "102", "punch_time": time_mark, "source": "PULL", "device_log_id": "DUP_ID"}
        )
        self.assertEqual(log_first.id, log_second.id)

    def test_impossible_future_punches_are_rejected(self):
        impossible_future_time = timezone.now() + timezone.timedelta(days=5)
        with self.assertRaises(DjangoValidationError):
            BiometricLogService.create_log(
                company=self.company,
                validated_data={"device": self.device, "device_user_id": "102", "punch_time": impossible_future_time, "source": "PULL"}
            )

    def test_pull_ingestion_generates_correct_batch_statistics(self):
        raw_vendor_payload = [
            {"uid": "102", "timestamp": timezone.now(), "device_log_id": "L1"},
            {"uid": "102", "timestamp": timezone.now(), "device_log_id": "L1"}, # Intentional duplicate
            {"uid": "UNKNOWN_ID", "timestamp": timezone.now(), "device_log_id": "L2"}
        ]
        
        batch_uuid = uuid.uuid4()
        res = BiometricPullIngestionService.ingest_device_logs(device=self.device, logs=raw_vendor_payload, batch_id=batch_uuid)
        
        self.assertEqual(res["sync_batch_id"], batch_uuid)
        self.assertEqual(res["statistics"]["created"], 2)
        self.assertEqual(res["statistics"]["duplicates"], 1)
        
        # Verify device operating synchronization markers updated cleanly
        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_synced_at)