from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.meetings.models.meeting import (
    Meeting,
)

from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.models.participant import (
    MeetingParticipant,
)

from apps.meetings.selectors.participant_selectors import (
    MeetingParticipantSelector,
)

from apps.meetings.integrations.rtc.factory import (
    RTCProviderFactory,
)


class MeetingSessionService:

    # =====================================================
    # RTC DATA
    # =====================================================

    @staticmethod
    def build_rtc_response(
        *,
        meeting,
        membership,
    ):

        rtc_provider = (
            RTCProviderFactory
            .get_provider(meeting.session.rtc_provider)
        )

        room_name = str(
            meeting.public_id
        )

        token_data = (

            rtc_provider
            .generate_token(

                room_name=room_name,

                participant_identity=str(
                    membership.id
                ),

                participant_name=(
                    membership.user.username
                ),
            )
        )

        return {

            "room_name": room_name,

            "rtc_provider": (
                meeting.session.rtc_provider
            ),

            "ws_url": (
                rtc_provider.ws_url
            ),

            "token": (
                token_data["token"]
            ),
        }

    # =====================================================
    # VALIDATE SESSION ACCESS
    # =====================================================

    @staticmethod
    def validate_session_access(
        *,
        meeting,
        membership,
    ):

        participant = (

            MeetingParticipantSelector
            .get_participant(
                meeting=meeting,
                membership=membership,
            )
        )

        if not participant:

            raise ValidationError(
                {
                    "detail": (
                        "You are not a participant "
                        "of this meeting."
                    )
                }
            )

        return participant

    # =====================================================
    # START SESSION
    # =====================================================

    @staticmethod
    @transaction.atomic
    def start_session(
        *,
        meeting,
        actor,
    ):

        session = meeting.session

        current_time = timezone.now()

        # =================================================
        # VALIDATE MANAGEMENT ACCESS
        # =================================================

        can_manage = (

            MeetingParticipantSelector
            .can_manage_meeting(

                meeting=meeting,

                membership=actor,
            )
        )

        if not can_manage:

            raise ValidationError(
                {
                    "detail": (
                        "You cannot start "
                        "this meeting."
                    )
                }
            )

        # =================================================
        # VALIDATE STATUS
        # =================================================

        if (
            session.session_status
            ==
            MeetingSession.SessionStatus.LIVE
        ):

            raise ValidationError(
                {
                    "detail": (
                        "Session already live."
                    )
                }
            )

        if (
            session.session_status
            ==
            MeetingSession.SessionStatus.ENDED
        ):

            raise ValidationError(
                {
                    "detail": (
                        "Ended session cannot "
                        "be restarted."
                    )
                }
            )

        # =================================================
        # CREATE RTC ROOM
        # =================================================

        rtc_provider = (
            RTCProviderFactory
            .get_provider(session.rtc_provider)
        )

        room_name = str(
            meeting.public_id
        )

        room_data = (

            rtc_provider
            .create_room(
                room_name=room_name,
            )
        )

        # =================================================
        # UPDATE SESSION
        # =================================================

        session.session_status = (
            MeetingSession
            .SessionStatus
            .LIVE
        )

        session.started_by = actor

        session.started_at = current_time

        session.rtc_room_id = (
            room_data["rtc_room_id"]
        )

        session.save(
            update_fields=[
                "session_status",
                "started_by",
                "started_at",
                "rtc_room_id",
                "updated_at",
            ]
        )

        # =================================================
        # UPDATE MEETING
        # =================================================

        meeting.status = (
            Meeting.Status.LIVE
        )

        meeting.started_at = (
            current_time
        )

        meeting.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

        # =================================================
        # HOST AUTO JOIN RTC
        # =================================================

        rtc_data = (

            MeetingSessionService
            .build_rtc_response(

                meeting=meeting,

                membership=actor,
            )
        )

        return {
            "session": session,
            "rtc": rtc_data,
        }

    # =====================================================
    # JOIN SESSION
    # =====================================================

    @staticmethod
    def join_session(
        *,
        meeting,
        membership,
    ):

        session = meeting.session

        # =================================================
        # VALIDATE LIVE SESSION
        # =================================================

        if (
            session.session_status
            !=
            MeetingSession.SessionStatus.LIVE
        ):

            raise ValidationError(
                {
                    "detail": (
                        "Meeting session "
                        "is not live."
                    )
                }
            )

        # =================================================
        # VALIDATE PARTICIPANT
        # =================================================

        participant = (

            MeetingSessionService
            .validate_session_access(

                meeting=meeting,

                membership=membership,
            )
        )

        # =================================================
        # GENERATE RTC TOKEN
        # =================================================

        rtc_data = (

            MeetingSessionService
            .build_rtc_response(

                meeting=meeting,

                membership=membership,
            )
        )

        return {
            "session": session,
            "participant": participant,
            "rtc": rtc_data,
        }

    # =====================================================
    # LEAVE SESSION
    # =====================================================

    @staticmethod
    def leave_session(
        *,
        meeting,
        membership,
    ):

        session = meeting.session

        participant = (

            MeetingSessionService
            .validate_session_access(

                meeting=meeting,

                membership=membership,
            )
        )

        participant.is_present = False

        participant.left_at = timezone.now()

        participant.status = (
            MeetingParticipant.Status.LEFT
        )

        participant.save(
            update_fields=[
                "is_present",
                "left_at",
                "status",
                "updated_at",
            ]
        )

        return session

    # =====================================================
    # END SESSION
    # =====================================================

    @staticmethod
    @transaction.atomic
    def end_session(
        *,
        meeting,
        actor,
    ):

        session = meeting.session

        current_time = timezone.now()

        can_manage = (

            MeetingParticipantSelector
            .can_manage_meeting(

                meeting=meeting,

                membership=actor,
            )
        )

        if not can_manage:

            raise ValidationError(
                {
                    "detail": (
                        "You cannot end "
                        "this meeting."
                    )
                }
            )

        if (
            session.session_status
            !=
            MeetingSession.SessionStatus.LIVE
        ):

            raise ValidationError(
                {
                    "detail": (
                        "Only live sessions "
                        "can be ended."
                    )
                }
            )

        # =================================================
        # DELETE RTC ROOM
        # =================================================

        rtc_provider = (
            RTCProviderFactory
            .get_provider(session.rtc_provider)
        )

        rtc_provider.delete_room(
            room_name=str(
                meeting.public_id
            )
        )

        # =================================================
        # UPDATE SESSION
        # =================================================

        session.session_status = (
            MeetingSession
            .SessionStatus
            .ENDED
        )

        session.ended_by = actor

        session.ended_at = current_time

        session.save(
            update_fields=[
                "session_status",
                "ended_by",
                "ended_at",
                "updated_at",
            ]
        )

        # =================================================
        # UPDATE MEETING
        # =================================================

        meeting.status = (
            Meeting.Status.COMPLETED
        )

        meeting.ended_at = (
            current_time
        )

        meeting.save(
            update_fields=[
                "status",
                "ended_at",
                "updated_at",
            ]
        )

        return session