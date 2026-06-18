import uuid
from typing import Any, Dict, List
from django.db import transaction
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.services.biometric_device_service import BiometricDeviceService
from apps.attendance.services.biometric_log_service import BiometricLogService


class BiometricPullIngestionService:
    """
    Normalizes and ingests raw punch logs collected from remote devices by background schedulers.
    """

    @classmethod
    @transaction.atomic
    def ingest_device_logs(cls, *, device: BiometricDevice, logs: List[Dict[str, Any]], batch_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        execution_batch_id = batch_id or uuid.uuid4()
        normalized_payloads = []

        for log in logs:
            normalized_payloads.append({
                "device": device,
                "device_user_id": log["uid"],
                "punch_time": log["timestamp"],
                "event_type": log.get("event_type", "UNKNOWN"),
                "device_log_id": log.get("device_log_id"),
                "source": "PULL",
                "sync_batch_id": execution_batch_id,
                "raw_payload": log
            })

        summary = BiometricLogService.bulk_create_logs(company=device.company, logs_data=normalized_payloads)
        
        # Update connection telemetry indicators tags on completion
        BiometricDeviceService.mark_synced(device=device)
        
        return {
            "sync_batch_id": execution_batch_id,
            "statistics": summary
        }