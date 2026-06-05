from datetime import timedelta

from django.utils import timezone

from apps.meetings.models.meeting import (
    Meeting,
)

from apps.meetings.selectors.participant_selectors import (
    MeetingParticipantSelector,
)

from apps.reminders.models.reminder import (
    Reminder,
)

from apps.reminders.services.reminder_service import (
    ReminderService,
)

from apps.reminders.validators.reminder_validator import (
    ReminderValidator,
)


class MeetingReminderService:

    # =====================================================
    # DEFAULT REMINDER RULES
    # =====================================================

    DEFAULT_REMINDER_MINUTES = [

        1440,  # 1 day

        60,    # 1 hour

        15,    # 15 minutes
    ]

    # =====================================================
    # CREATE MEETING REMINDERS
    # =====================================================

    @classmethod
    def create_meeting_reminders(
        cls,
        *,
        meeting,
        reminder_minutes=None,
    ):

        if meeting.status in [

            Meeting.Status.CANCELLED,

            Meeting.Status.COMPLETED,
        ]:

            return []

        reminder_minutes = sorted(

            set(

                reminder_minutes

                or

                cls.DEFAULT_REMINDER_MINUTES
            )
        )

        participants = (

            MeetingParticipantSelector
            .get_meeting_participants(
                meeting=meeting,
            )
        )

        reminder_payloads = []

        for participant in participants:

            for minutes_before in reminder_minutes:

                if (

                    minutes_before

                    not in

                    ReminderValidator.ALLOWED_MINUTES

                ):

                    continue

                remind_at = (

                    meeting.scheduled_start

                    - timedelta(
                        minutes=minutes_before,
                    )
                )

                if remind_at <= timezone.now():

                    continue

                reminder_payloads.append(

                    {

                        "company":
                        meeting.company,

                        "recipient_membership":
                        participant.membership,

                        "target_type":
                        Reminder.TargetType.MEETING,

                        "target_id":
                        meeting.id,

                        "remind_at":
                        remind_at,

                        "minutes_before":
                        minutes_before,

                        "metadata": {

                            "meeting_id":
                            meeting.id,

                            "meeting_public_id":
                            str(
                                meeting.public_id
                            ),

                            "meeting_title":
                            meeting.title,
                        },
                    }
                )

        if not reminder_payloads:

            return []

        return (

            ReminderService
            .create_bulk_reminders(
                reminders=reminder_payloads,
            )
        )

    # =====================================================
    # REGENERATE MEETING REMINDERS
    # =====================================================

    @classmethod
    def regenerate_meeting_reminders(
        cls,
        *,
        meeting,
        reminder_minutes=None,
    ):

        ReminderService.cancel_target_reminders(

            target_type=
            Reminder.TargetType.MEETING,

            target_id=meeting.id,
        )

        return (

            cls.create_meeting_reminders(
                meeting=meeting,
                reminder_minutes=(
                    reminder_minutes
                ),
            )
        )

    # =====================================================
    # CANCEL MEETING REMINDERS
    # =====================================================

    @classmethod
    def cancel_meeting_reminders(
        cls,
        *,
        meeting,
    ):

        return (

            ReminderService
            .cancel_target_reminders(

                target_type=
                Reminder.TargetType.MEETING,

                target_id=meeting.id,
            )
        )