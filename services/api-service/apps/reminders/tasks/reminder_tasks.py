from celery import shared_task

from apps.meetings.selectors.meeting_selectors import (
    MeetingSelector,
)

from apps.reminders.models.reminder import (
    Reminder,
)

from apps.reminders.selectors.reminder_selector import (
    ReminderSelector,
)

from apps.reminders.handlers.meeting_reminder_handler import (
    MeetingReminderHandler,
)

from apps.reminders.services.reminder_service import (
    ReminderService,
)


@shared_task(
    bind=True,
)
def process_due_reminders(
    self,
):

    reminders = (
        ReminderSelector
        .get_due_reminders()
    )

    for reminder in reminders:

        try:

            ReminderService.mark_processing(
                reminder=reminder,
            )

            _process_reminder(
                reminder=reminder,
            )

            ReminderService.mark_sent(
                reminder=reminder,
            )

        except Exception as exc:

            ReminderService.mark_failed(
                reminder=reminder,
                reason=str(exc),
            )

            continue


# =====================================================
# ROUTER
# =====================================================

def _process_reminder(
    *,
    reminder,
):

    if (
        reminder.target_type
        ==
        Reminder.TargetType.MEETING
    ):

        _process_meeting_reminder(
            reminder=reminder,
        )

        return

    raise ValueError(
        f"Unsupported reminder type: "
        f"{reminder.target_type}"
    )


# =====================================================
# MEETING REMINDER
# =====================================================

def _process_meeting_reminder(
    *,
    reminder,
):

    meeting = (
        MeetingSelector
        .get_by_id(
            meeting_id=reminder.target_id,
        )
    )

    if not meeting:
        return

    MeetingReminderHandler.handle(
        reminder=reminder,
        meeting=meeting,
    )