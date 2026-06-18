import django.utils.timezone as timezone
from typing import Any, Dict, List, Optional
from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.models.biometric_log import BiometricLog, ProcessingStatusChoices
from apps.attendance.validators.biometric_log_validator import BiometricLogValidator
from apps.attendance.selectors.biometric_log_selector import BiometricLogSelector
from apps.attendance.selectors.biometric_employee_mapping_selector import BiometricEmployeeMappingSelector


class BiometricLogService:
    """
    Orchestrates ingestion processing pipelines for raw physical log streams.
    """

    @classmethod
    @transaction.atomic
    def create_log(cls, *, company: Company, validated_data: Dict[str, Any]) -> BiometricLog:
        """
        Validates, normalizes identity maps, and registers incoming hardware signals.
        Returns the existing matching log instance safely if an ingestion duplicate is detected.
        """
        device = validated_data.get("device")
        device_log_id = validated_data.get("device_log_id")
        device_user_id = str(validated_data["device_user_id"]).strip()

        # Step 1: Idempotency check to avoid generating redundant entries
        if device and device_log_id:
            duplicate = BiometricLogSelector.find_duplicate(company=company, device=device, device_log_id=device_log_id)
            if duplicate:
                return duplicate

        # Step 2: Resolve identity mapping across user space partitions
        membership = None
        if device:
            mapping = BiometricEmployeeMappingSelector.find_by_device_identity(
                company=company, 
                device=device, 
                device_user_id=device_user_id
            )
            if mapping:
                membership = mapping.membership

        # Step 3: Run structural format boundary check routines
        BiometricLogValidator.validate_log_payload_parameters(validated_data)
        BiometricLogValidator.validate_entity_tenant_alignment(company, device=device, membership=membership)

        return BiometricLog.objects.create(
            company=company,
            device=device,
            membership=membership,
            device_user_id=device_user_id,
            event_type=validated_data.get("event_type", "UNKNOWN"),
            punch_time=validated_data["punch_time"],
            device_log_id=device_log_id,
            source=validated_data["source"],
            raw_payload=validated_data.get("raw_payload", {}),
            sync_batch_id=validated_data.get("sync_batch_id"),
            processing_status=validated_data.get("processing_status", ProcessingStatusChoices.PENDING)
        )

    @classmethod
    @transaction.atomic
    def bulk_create_logs(cls, *, company: Company, logs_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingests batches of logging data. Captures exceptions and returns 
        processing tracking summaries instead of rolling back the entire transaction payload.
        """
        metrics = {"total": len(logs_data), "created": 0, "duplicates": 0, "failed": 0}

        for single_log_payload in logs_data:
            try:
                # Wrap each log statement execution inside a separate savepoint transaction lock block
                with transaction.atomic():
                    device = single_log_payload.get("device")
                    device_log_id = single_log_payload.get("device_log_id")

                    if device and device_log_id:
                        duplicate = BiometricLogSelector.find_duplicate(company=company, device=device, device_log_id=device_log_id)
                        if duplicate:
                            metrics["duplicates"] += 1
                            continue

                    cls.create_log(company=company, validated_data=single_log_payload)
                    metrics["created"] += 1

            except Exception:
                metrics["failed"] += 1
                continue

        return metrics

    @classmethod
    @transaction.atomic
    def mark_processed(cls, *, log: BiometricLog) -> BiometricLog:
        log.processing_status = ProcessingStatusChoices.PROCESSED
        log.processed_at = timezone.now()
        log.save(update_fields=["processing_status", "processed_at", "updated_at"])
        return log

    @classmethod
    @transaction.atomic
    def mark_failed(cls, *, log: BiometricLog, reason: str) -> BiometricLog:
        log.processing_status = ProcessingStatusChoices.FAILED
        log.failure_reason = reason
        log.save(update_fields=["processing_status", "failure_reason", "updated_at"])
        return log

    @classmethod
    @transaction.atomic
    def mark_ignored(cls, *, log: BiometricLog, reason: str) -> BiometricLog:
        log.processing_status = ProcessingStatusChoices.IGNORED
        log.failure_reason = reason
        log.save(update_fields=["processing_status", "failure_reason", "updated_at"])
        return log