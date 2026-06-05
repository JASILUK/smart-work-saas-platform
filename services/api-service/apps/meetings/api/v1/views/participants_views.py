from apps.meetings.api.v1.mixins.participants_mixin import MeetingParticipantManagementMixin
from rest_framework.request import Request

from apps.core.api_response import (
    ApiResponse,
)


from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.meetings.api.v1.serializers.participants_serializers import (
    MeetingParticipantAddSerializer,
    MeetingParticipantOutputSerializer,
    MeetingParticipantRoleUpdateSerializer,
)



from apps.meetings.selectors.participant_selectors import (
    MeetingParticipantSelector,
)

from apps.meetings.services.participant_service import (
    MeetingParticipantService,
)





# =========================================================
# PARTICIPANT LIST + CREATE
# =========================================================

class MeetingParticipantListCreateAPI(
    MeetingParticipantManagementMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

    "GET": "tenant.meeting.view",
    }

    # =====================================================
    # LIST PARTICIPANTS
    # =====================================================

    def get(
        self,
        request: Request,
        public_id,
    ):

        meeting = self.get_meeting(

            request=request,

            public_id=public_id,
        )

        participants = (

            MeetingParticipantSelector
            .get_meeting_participants(
                meeting=meeting,
            )
        )

        serializer = (

            MeetingParticipantOutputSerializer(

                participants,

                many=True,
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )

    # =====================================================
    # ADD PARTICIPANTS
    # =====================================================

    def post(
        self,
        request: Request,
        public_id,
    ):

        meeting = self.get_meeting(

            request=request,

            public_id=public_id,
        )

        self.validate_management_access(

            meeting=meeting,

            membership=request.membership,
        )

        serializer = (

            MeetingParticipantAddSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        MeetingParticipantService.add_participants(

            meeting=meeting,

            membership_ids=(
                serializer.validated_data[
                    "membership_ids"
                ]
            ),

            invited_by=request.membership,
        )

        participants = (

            MeetingParticipantSelector
            .get_meeting_participants(
                meeting=meeting,
            )
        )

        response_serializer = (

            MeetingParticipantOutputSerializer(

                participants,

                many=True,
            )
        )

        return ApiResponse.success(

            data=response_serializer.data,

            message="Participants added.",

            status=201,
        )


# =========================================================
# PARTICIPANT DETAIL MANAGEMENT
# =========================================================

class MeetingParticipantDetailAPI(
    MeetingParticipantManagementMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

    "GET": "tenant.meeting.view",
    }

    # =====================================================
    # UPDATE ROLE
    # =====================================================

    def patch(
        self,
        request: Request,
        public_id,
        participant_id,
    ):

        meeting = self.get_meeting(

            request=request,

            public_id=public_id,
        )

        self.validate_management_access(

            meeting=meeting,

            membership=request.membership,
        )

        participant = self.get_participant(

            meeting=meeting,

            participant_id=participant_id,
        )

        serializer = (

            MeetingParticipantRoleUpdateSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        participant = (

            MeetingParticipantService
            .update_participant_role(

                actor=request.membership,

                participant=participant,

                role=serializer.validated_data["role"],
            )
        )

        response_serializer = (

            MeetingParticipantOutputSerializer(
                participant,
            )
        )

        return ApiResponse.success(

            data=response_serializer.data,

            message="Participant updated.",
        )

    # =====================================================
    # REMOVE PARTICIPANT
    # =====================================================

    def delete(
        self,
        request: Request,
        public_id,
        participant_id,
    ):

        meeting = self.get_meeting(

            request=request,

            public_id=public_id,
        )

        self.validate_management_access(

            meeting=meeting,

            membership=request.membership,
        )

        participant = self.get_participant(

            meeting=meeting,

            participant_id=participant_id,
        )

        MeetingParticipantService.remove_participant(
            participant=participant,
        )

        return ApiResponse.success(
            message="Participant removed.",
        )