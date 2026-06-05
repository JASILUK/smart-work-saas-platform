from django.db import transaction
from django.utils import timezone

from apps.reminders.models.reminder import (
    Reminder,
)

from apps.reminders.validators.reminder_validator import (
    ReminderValidator,
)


class ReminderService:

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create_reminder(
        *,
        company,
        recipient_membership,
        target_type,
        target_id,
        remind_at,
        minutes_before=0,
        metadata=None,
    ):

        ReminderValidator.validate_create(
            company=company,
            recipient_membership=recipient_membership,
            target_type=target_type,
            target_id=target_id,
            remind_at=remind_at,
            minutes_before=minutes_before,
        )

        return Reminder.objects.create(
            company=company,
            recipient_membership=recipient_membership,
            target_type=target_type,
            target_id=target_id,
            remind_at=remind_at,
            minutes_before=minutes_before,
            metadata=metadata or {},
        )

    # =====================================================
    # BULK CREATE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_bulk_reminders(
        *,
        reminders,
    ):

        reminder_objects = [

            Reminder(
                company=item["company"],
                recipient_membership=(
                    item["recipient_membership"]
                ),
                target_type=item["target_type"],
                target_id=item["target_id"],
                remind_at=item["remind_at"],
                minutes_before=item.get(
                    "minutes_before",
                    0,
                ),
                metadata=item.get(
                    "metadata",
                    {},
                ),
            )

            for item in reminders
        ]

        return Reminder.objects.bulk_create(
            reminder_objects,
        )

    # =====================================================
    # MARK PROCESSING
    # =====================================================

    @staticmethod
    def mark_processing(
        *,
        reminder,
    ):

        ReminderValidator.validate_processing(
            reminder=reminder,
        )

        reminder.status = (
            Reminder.Status.PROCESSING
        )

        reminder.save(
            update_fields=[
                "status",
            ],
        )

        return reminder

    # =====================================================
    # MARK SENT
    # =====================================================

    @staticmethod
    def mark_sent(
        *,
        reminder,
    ):

        ReminderValidator.validate_sent(
            reminder=reminder,
        )

        reminder.status = (
            Reminder.Status.SENT
        )

        reminder.processed_at = (
            timezone.now()
        )

        reminder.failure_reason = ""

        reminder.save(
            update_fields=[
                "status",
                "processed_at",
                "failure_reason",
            ],
        )

        return reminder

    # =====================================================
    # MARK FAILED
    # =====================================================

    @staticmethod
    def mark_failed(
        *,
        reminder,
        reason,
    ):

        ReminderValidator.validate_failed(
            reminder=reminder,
        )

        reminder.status = (
            Reminder.Status.FAILED
        )

        reminder.failure_reason = str(
            reason
        )

        reminder.processed_at = (
            timezone.now()
        )

        reminder.save(
            update_fields=[
                "status",
                "failure_reason",
                "processed_at",
            ],
        )

        return reminder

    # =====================================================
    # CANCEL
    # =====================================================

    @staticmethod
    def cancel_reminder(
        *,
        reminder,
    ):

        ReminderValidator.validate_cancel(
            reminder=reminder,
        )

        reminder.status = (
            Reminder.Status.CANCELLED
        )

        reminder.save(
            update_fields=[
                "status",
            ],
        )

        return reminder

    # =====================================================
    # CANCEL TARGET REMINDERS
    # =====================================================

    @staticmethod
    def cancel_target_reminders(
        *,
        target_type,
        target_id,
    ):

        return (

            Reminder.objects

            .filter(
                target_type=target_type,
                target_id=target_id,
                status__in=[
                    Reminder.Status.PENDING,
                    Reminder.Status.PROCESSING,
                ],
            )

            .update(
                status=Reminder.Status.CANCELLED,
            )
        )