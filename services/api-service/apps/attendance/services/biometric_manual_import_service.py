import uuid
from typing import Any, Dict, List
from django.db import transaction
from apps.companies.models import Company
from apps.attendance.services.biometric_log_service import BiometricLogService


class BiometricManualImportService:
    """
    Normalizes text-parsed matrices or CSV file streams uploaded manually by administrators.
    """

    @classmethod
    @transaction.atomic
    def import_logs(cls, *, company: Company, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        execution_batch_id = uuid.uuid4()
        normalized_payloads = []

        for row in rows:
            normalized_payloads.append({
                "device": None, # Manual file uploads lack direct terminal context binds
                "device_user_id": row["device_user_id"],
                "punch_time": row["punch_time"],
                "event_type": row.get("event_type", "UNKNOWN"),
                "device_log_id": f"MANUAL-{execution_batch_id}-{row['device_user_id']}-{row['punch_time']}",
                "source": "MANUAL",
                "sync_batch_id": execution_batch_id,
                "raw_payload": row
            })

        summary = BiometricLogService.bulk_create_logs(company=company, logs_data=normalized_payloads)
        return {
            "sync_batch_id": execution_batch_id,
            "statistics": summary
        }