from django.utils import timezone

from apps.meetings.models.meeting import (
    Meeting,
)

from apps.notifications.services.notification_service import (
    NotificationService,
)


class MeetingReminderHandler:

    # =====================================================
    # HANDLE
    # =====================================================

    @classmethod
    def handle(
        cls,
        *,
        reminder,
        meeting,
    ):

        if (
            meeting.status
            == Meeting.Status.CANCELLED
        ):
            return

        if (
            meeting.status
            == Meeting.Status.COMPLETED
        ):
            return

        membership = (
            reminder.recipient_membership
        )

        NotificationService.send_meeting_notification(

            membership=membership,

            title=cls._build_title(
                reminder=reminder,
                meeting=meeting,
            ),

            body=cls._build_body(
                reminder=reminder,
                meeting=meeting,
            ),

            data=cls._build_data(
                reminder=reminder,
                meeting=meeting,
            ),
        )

    # =====================================================
    # TITLE
    # =====================================================

    @staticmethod
    def _build_title(
        *,
        reminder,
        meeting,
    ):

        minutes = (
            reminder.minutes_before
        )

        if minutes >= 1440:

            days = (
                minutes // 1440
            )

            return (
                f"Meeting starts in "
                f"{days} day"
                f"{'s' if days > 1 else ''}"
            )

        if minutes >= 60:

            hours = (
                minutes // 60
            )

            return (
                f"Meeting starts in "
                f"{hours} hour"
                f"{'s' if hours > 1 else ''}"
            )

        return (
            f"Meeting starts in "
            f"{minutes} minutes"
        )

    # =====================================================
    # BODY
    # =====================================================

    @staticmethod
    def _build_body(
        *,
        reminder,
        meeting,
    ):

        start_time = (
            timezone.localtime(
                meeting.scheduled_start
            )
            .strftime(
                "%d %b %Y %I:%M %p"
            )
        )

        return (
            f"{meeting.title} "
            f"starts at "
            f"{start_time}."
        )

    # =====================================================
    # DATA
    # =====================================================

    @staticmethod
    def _build_data(
        *,
        reminder,
        meeting,
    ):

        return {

            "meeting_id":
            meeting.id,

            "meeting_public_id":
            str(
                meeting.public_id
            ),

            "minutes_before":
            reminder.minutes_before,

            "scheduled_start":
            meeting.scheduled_start.isoformat(),

            "type":
            "meeting_reminder",
        }