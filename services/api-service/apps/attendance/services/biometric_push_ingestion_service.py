import uuid
from typing import Any, Dict, List
from django.db import transaction
from apps.companies.models import Company
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.services.biometric_log_service import BiometricLogService


class BiometricPushIngestionService:
    """
    Processes real-time log payloads pushed to webhook targets by cloud-connected devices.
    """

    @classmethod
    @transaction.atomic
    def ingest_payload(cls, *, company: Company, device: BiometricDevice, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        execution_batch_id = uuid.uuid4()
        normalized_payloads = []

        for item in payload:
            normalized_payloads.append({
                "device": device,
                "device_user_id": item["uid"],
                "punch_time": item["timestamp"],
                "event_type": item.get("event_type", "UNKNOWN"),
                "device_log_id": item.get("device_log_id"),
                "source": "PUSH",
                "sync_batch_id": execution_batch_id,
                "raw_payload": item
            })

        summary = BiometricLogService.bulk_create_logs(company=company, logs_data=normalized_payloads)
        return {
            "sync_batch_id": execution_batch_id,
            "statistics": summary
        }