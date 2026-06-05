from django.utils import timezone

from apps.meetings.models.participant import (
    MeetingParticipant,
)

from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.realtime.broad_cast_service import MeetingRealtimeService
from apps.meetings.selectors.session_selectors import (
    MeetingSessionSelector,
)

from apps.meetings.tasks.meeting_tasks import (
    auto_end_empty_meeting_task,
)


class RTCEventService:

    # =====================================================
    # HANDLE EVENT
    # =====================================================

    @classmethod
    def handle_event(
        cls,
        *,
        rtc_event,
    ):

        handlers = {

            "participant_joined": (
                cls.handle_participant_joined
            ),

            "participant_left": (
                cls.handle_participant_left
            ),

            "room_finished": (
                cls.handle_room_finished
            ),
        }

        handler = handlers.get(
            rtc_event.event_type,
        )

        if handler:

            handler(
                rtc_event=rtc_event,
            )

    # =====================================================
    # PARTICIPANT JOINED
    # =====================================================

    @staticmethod
    def handle_participant_joined(
        *,
        rtc_event,
    ):

        session = (

            MeetingSessionSelector
            .get_by_room_id(
                rtc_room_id=rtc_event.room_id,
            )
        )

        if not session:
            return

        participant = (

            MeetingParticipant.objects

            .filter(
                meeting=session.meeting,

                membership_id=(
                    rtc_event
                    .participant_identity
                ),
            )

            .first()
        )

        if not participant:
            return

        participant.is_present = True

        participant.joined_at = timezone.now()

        participant.status = (
            MeetingParticipant
            .Status
            .JOINED
        )

        participant.joined_count += 1

        participant.save(
            update_fields=[
                "is_present",
                "joined_at",
                "status",
                "joined_count",
                "updated_at",
            ]
        )

        MeetingRealtimeService.broadcast_participant_joined(
            tenant_id=session.meeting.company_id,
            meeting_id=session.meeting.id,
            participant=participant,
        )


    # =====================================================
    # PARTICIPANT LEFT
    # =====================================================

    @staticmethod
    def handle_participant_left(
        *,
        rtc_event,
    ):

        session = (

            MeetingSessionSelector
            .get_by_room_id(
                rtc_room_id=rtc_event.room_id,
            )
        )

        if not session:
            return

        participant = (

            MeetingParticipant.objects

            .filter(
                meeting=session.meeting,

                membership_id=(
                    rtc_event
                    .participant_identity
                ),
            )

            .first()
        )

        if not participant:
            return

        participant.is_present = False

        participant.left_at = timezone.now()

        participant.status = (
            MeetingParticipant
            .Status
            .LEFT
        )

        participant.save(
            update_fields=[
                "is_present",
                "left_at",
                "status",
                "updated_at",
            ]
        )

        MeetingRealtimeService.broadcast_participant_left(
            tenant_id=session.meeting.company_id,
            meeting_id=session.meeting.id,
            membership_id=participant.membership_id,
        )

        # =================================================
        # AUTO END CHECK
        # =================================================

        has_active_participants = (

            MeetingParticipant.objects

            .filter(
                meeting=session.meeting,
                is_present=True,
            )

            .exists()
        )

        if not has_active_participants:

            auto_end_empty_meeting_task.apply_async(
                kwargs={
                    "session_id": session.id,
                },
                countdown=300,
            )

    # =====================================================
    # ROOM FINISHED
    # =====================================================

    @staticmethod
    def handle_room_finished(
        *,
        rtc_event,
    ):

        session = (

            MeetingSessionSelector
            .get_by_room_id(
                rtc_room_id=rtc_event.room_id,
            )
        )

        if not session:
            return

        if (

            session.session_status
            ==
            MeetingSession.SessionStatus.ENDED
        ):

            return

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

        MeetingRealtimeService.broadcast_meeting_ended(
            tenant_id=session.meeting.company_id,
            meeting_id=session.meeting.id,
        )