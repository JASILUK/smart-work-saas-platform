from django.utils import timezone

from celery import shared_task

from apps.meetings.models.participant import (
    MeetingParticipant,
)

from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.selectors.session_selectors import (
    MeetingSessionSelector,
)


@shared_task
def auto_end_empty_meeting_task(
    *,
    session_id,
):

    session = (

        MeetingSessionSelector
        .base_queryset()

        .filter(
            id=session_id,
        )

        .first()
    )

    if not session:
        return

    if (

        session.session_status
        !=
        MeetingSession.SessionStatus.LIVE
    ):

        return

    has_active_participants = (

        MeetingParticipant.objects

        .filter(
            meeting=session.meeting,
            is_present=True,
        )

        .exists()
    )

    # =====================================================
    # STILL EMPTY
    # =====================================================

    if not has_active_participants:

        session.session_status = (
            MeetingSession
            .SessionStatus
            .ENDED
        )

        session.ended_at = timezone.now()

        session.save(
            update_fields=[
                "session_status",
                "ended_at",
                "updated_at",
            ]
        )

        meeting = session.meeting

        meeting.status = (
            meeting.Status.COMPLETED
        )

        meeting.ended_at = timezone.now()

        meeting.save(
            update_fields=[
                "status",
                "ended_at",
                "updated_at",
            ]
        )