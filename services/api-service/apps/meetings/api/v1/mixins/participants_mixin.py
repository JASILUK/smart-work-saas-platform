# =========================================================
# PARTICIPANT MANAGEMENT MIXIN
# =========================================================

from apps.core.exceptions import NotFoundError, PermissionDeniedError
from apps.meetings.selectors.meeting_selectors import MeetingSelector
from apps.meetings.selectors.participant_selectors import MeetingParticipantSelector


class MeetingParticipantManagementMixin:

    # =====================================================
    # GET MEETING
    # =====================================================

    def get_meeting(
        self,
        *,
        request,
        public_id,
    ):

        meeting = (

            MeetingSelector
            .get_by_public_id(

                public_id=public_id,

                company=request.company,
            )
        )

        if not meeting:

            raise NotFoundError(
                message="Meeting not found."
            )

        return meeting

    # =====================================================
    # GET PARTICIPANT
    # =====================================================

    def get_participant(
        self,
        *,
        meeting,
        participant_id,
    ):

        participant = (

            MeetingParticipantSelector
            .get_by_id(

                meeting=meeting,

                participant_id=participant_id,
            )
        )

        if not participant:

            raise NotFoundError(
                message="Participant not found."
            )

        return participant

    # =====================================================
    # VALIDATE MANAGEMENT ACCESS
    # =====================================================

    def validate_management_access(
        self,
        *,
        meeting,
        membership,
    ):

        can_manage = (

            MeetingParticipantSelector
            .can_manage_meeting(

                meeting=meeting,

                membership=membership,
            )
        )

        if not can_manage:

            raise PermissionDeniedError(
                message=(
                    "You cannot manage "
                    "this meeting."
                )
            )