from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.reminders.models.reminder import (
    Reminder,
)


class ReminderValidator:

    # =====================================================
    # ALLOWED REMINDER VALUES
    # =====================================================

    ALLOWED_MINUTES = [

        5,
        10,
        15,
        30,

        60,
        120,

        1440,

        10080,
    ]

    # =====================================================
    # VALIDATE CREATE
    # =====================================================

    @classmethod
    def validate_create(
        cls,
        *,
        company,
        recipient_membership,
        target_type,
        target_id,
        remind_at,
        minutes_before,
    ):

        if company is None:

            raise ValidationError(
                "Company is required."
            )

        if recipient_membership is None:

            raise ValidationError(
                "Recipient membership is required."
            )

        if not target_type:

            raise ValidationError(
                "Target type is required."
            )

        if not target_id:

            raise ValidationError(
                "Target id is required."
            )

        if remind_at is None:

            raise ValidationError(
                "Reminder datetime is required."
            )

        if (
            minutes_before
            not in cls.ALLOWED_MINUTES
        ):

            raise ValidationError(
                (
                    "Invalid reminder value."
                )
            )

    # =====================================================
    # VALIDATE STATUS TRANSITION
    # =====================================================

    @staticmethod
    def validate_processing(
        *,
        reminder,
    ):

        if (
            reminder.status
            != Reminder.Status.PENDING
        ):

            raise ValidationError(
                (
                    "Only pending reminders "
                    "can be processed."
                )
            )

    @staticmethod
    def validate_sent(
        *,
        reminder,
    ):

        if (
            reminder.status
            != Reminder.Status.PROCESSING
        ):

            raise ValidationError(
                (
                    "Reminder must be "
                    "processing before sent."
                )
            )

    @staticmethod
    def validate_failed(
        *,
        reminder,
    ):

        if (
            reminder.status
            != Reminder.Status.PROCESSING
        ):

            raise ValidationError(
                (
                    "Reminder must be "
                    "processing before failed."
                )
            )

    @staticmethod
    def validate_cancel(
        *,
        reminder,
    ):

        if reminder.status in [

            Reminder.Status.SENT,

            Reminder.Status.CANCELLED,
        ]:

            raise ValidationError(
                (
                    "Reminder cannot "
                    "be cancelled."
                )
            )