from django.utils import timezone

from apps.reminders.models.reminder import (
Reminder,
)

class ReminderSelector:


    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def base_queryset():

        return (

            Reminder.objects

            .select_related(
                "company",
                "recipient_membership",
                "recipient_membership__user",
            )
        )

    # =====================================================
    # GET BY ID
    # =====================================================

    @classmethod
    def get_by_id(
        cls,
        *,
        reminder_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                id=reminder_id,
            )

            .first()
        )

    # =====================================================
    # GET DUE REMINDERS
    # =====================================================

    @classmethod
    def get_due_reminders(
        cls,
        *,
        current_time=None,
    ):

        current_time = (
            current_time
            or timezone.now()
        )

        return (

            cls.base_queryset()

            .filter(
                status=Reminder.Status.PENDING,
                remind_at__lte=current_time,
            )

            .order_by(
                "remind_at",
            )
        )

    # =====================================================
    # GET PENDING REMINDERS
    # =====================================================

    @classmethod
    def get_pending_reminders(
        cls,
    ):

        return (

            cls.base_queryset()

            .filter(
                status=Reminder.Status.PENDING,
            )

            .order_by(
                "remind_at",
            )
        )

    # =====================================================
    # GET REMINDERS FOR RECIPIENT
    # =====================================================

    @classmethod
    def get_for_membership(
        cls,
        *,
        membership,
    ):

        return (

            cls.base_queryset()

            .filter(
                recipient_membership=membership,
            )

            .order_by(
                "-remind_at",
            )
        )

    # =====================================================
    # GET TARGET REMINDERS
    # =====================================================

    @classmethod
    def get_target_reminders(
        cls,
        *,
        target_type,
        target_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                target_type=target_type,
                target_id=target_id,
            )

            .order_by(
                "-created_at",
            )
        )

    # =====================================================
    # GET ACTIVE TARGET REMINDERS
    # =====================================================

    @classmethod
    def get_active_target_reminders(
        cls,
        *,
        target_type,
        target_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                target_type=target_type,
                target_id=target_id,

                status__in=[
                    Reminder.Status.PENDING,
                    Reminder.Status.PROCESSING,
                ],
            )

            .order_by(
                "remind_at",
            )
        )

    # =====================================================
    # EXISTS
    # =====================================================

    @classmethod
    def exists(
        cls,
        *,
        target_type,
        target_id,
        membership,
        remind_at,
    ):

        return (

            cls.base_queryset()

            .filter(
                target_type=target_type,
                target_id=target_id,
                recipient_membership=membership,
                remind_at=remind_at,
            )

            .exists()
        )

