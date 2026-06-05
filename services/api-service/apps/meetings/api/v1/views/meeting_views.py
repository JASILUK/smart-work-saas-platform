from rest_framework.request import Request

from apps.core.api_response import (
    ApiResponse,
)

from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.meetings.api.v1.mixins.meeting_mixin import (
    MeetingAccessMixin,
)

from apps.meetings.api.v1.serializers.meeting_serializer import (
    MeetingCreateSerializer,
    MeetingDetailSerializer,
    MeetingListSerializer,
    MeetingTargetInputSerializer,
    MeetingUpdateSerializer,
)

from apps.meetings.selectors.meeting_selectors import (
    MeetingSelector,
)

from apps.meetings.selectors.target_selectors import (
    MeetingTargetSelector,
)

from apps.meetings.services.meeting_service import (
    MeetingService,
)

from apps.meetings.services.target_service import (
    MeetingTargetService,
)




class MeetingListCreateAPI(
    MeetingAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

        "GET": "tenant.meeting.view",

        "POST": "tenant.meeting.create",
    }

    # =====================================================
    # LIST
    # =====================================================

    def get(
        self,
        request: Request,
    ):

        search = request.query_params.get(
            "search"
        )

        status = request.query_params.get(
            "status"
        )

        ordering = request.query_params.get(
            "ordering",
            "-scheduled_start",
        )

        meetings = (

            MeetingSelector
            .get_visible_meetings_for_membership(

                membership=request.membership,

                search=search,

                status=status,

                ordering=ordering,
            )
        )

        serializer = (

            MeetingListSerializer(
                meetings,
                many=True,

                context={
                    "request": request,
                },
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )

    # =====================================================
    # CREATE
    # =====================================================

    def post(
        self,
        request: Request,
    ):

        serializer = (

            MeetingCreateSerializer(
                data=request.data,
                context={
                    "request": request,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        meeting = (

            MeetingService
            .create_meeting(
                company=request.company,
                membership=request.membership,
                validated_data=serializer.validated_data,
            )
        )

        meeting = (

            MeetingSelector
            .get_by_public_id(
                public_id=meeting.public_id,
                company=request.company,
            )
        )

        return ApiResponse.success(

            data=self.serialize_meeting(
                request= request,
                meeting=meeting,
            ),

            message="Meeting created.",

            status=201,
        )
    


class MeetingDetailAPI(
    MeetingAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

    "GET": "tenant.meeting.view",
    }

    # =====================================================
    # DETAIL
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

        return ApiResponse.success(

            data=self.serialize_meeting(
                request=request,
                meeting=meeting,
            )
        )

    # =====================================================
    # UPDATE
    # =====================================================

    def patch(
        self,
        request: Request,
        public_id,
    ):

        meeting = self.get_meeting(
            request=request,
            public_id=public_id,
        )

        self.require_management_access(
            meeting=meeting,
            membership=request.membership,
        )

        serializer = (

            MeetingUpdateSerializer(

                instance=meeting,

                data=request.data,

                partial=True,

                context={
                    "request": request,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        meeting = (

            MeetingService
            .update_meeting(

                meeting=meeting,

                validated_data=serializer.validated_data,

                updated_by_membership=request.membership,
            )
        )

        meeting = (

            MeetingSelector
            .get_by_public_id(
                public_id=meeting.public_id,
                company=request.company,
            )
        )

        return ApiResponse.success(

            data=self.serialize_meeting(
                request=request,
                meeting=meeting,
            ),

            message="Meeting updated.",
        )

    # =====================================================
    # CANCEL
    # =====================================================

    def delete(
        self,
        request: Request,
        public_id,
    ):

        meeting = self.get_meeting(
            request=request,
            public_id=public_id,
        )

        self.require_management_access(
            meeting=meeting,
            membership=request.membership,
        )

        MeetingService.cancel_meeting(

            meeting=meeting,

            cancelled_by=request.membership,

            reason=request.data.get(
                "reason",
                "",
            ),
        )

        return ApiResponse.success(
            message="Meeting cancelled.",
        )






class MeetingTargetListCreateAPI(
    MeetingAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

    "GET": "tenant.meeting.view",
    }

    # =====================================================
    # LIST TARGETS
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

        targets = (

            MeetingTargetSelector
            .get_meeting_targets(
                meeting=meeting,
            )
        )

        return ApiResponse.success(

            data=self.serialize_targets(
                meeting=meeting,
                targets=targets,
            )
        )

    # =====================================================
    # ADD TARGET
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

        self.require_management_access(
            meeting=meeting,
            membership=request.membership,
        )

        serializer = (
            MeetingTargetInputSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        target = (

            MeetingTargetService
            .add_target(

                meeting=meeting,

                company=request.company,

                created_by_membership=request.membership,

                target_data=serializer.validated_data,
            )
        )

        return ApiResponse.success(

            data=self.serialize_target(
                meeting=meeting,
                target=target,
            ),

            message="Target added.",

            status=201,
        )
    

class MeetingTargetDetailAPI(
    MeetingAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

    "GET": "tenant.meeting.view",
    }

    # =====================================================
    # UPDATE TARGET
    # =====================================================

    def patch(
        self,
        request: Request,
        public_id,
        target_id,
    ):

        meeting = self.get_meeting(
            request=request,
            public_id=public_id,
        )

        self.require_management_access(
            meeting=meeting,
            membership=request.membership,
        )

        target = self.get_target(
            meeting=meeting,
            target_id=target_id,
        )

        serializer = (
            MeetingTargetInputSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        target = (

            MeetingTargetService
            .update_target(

                company=request.company,

                target=target,

                validated_data=serializer.validated_data,
            )
        )

        return ApiResponse.success(

            data=self.serialize_target(
                meeting=meeting,
                target=target,
            ),

            message="Target updated.",
        )
    

    # =====================================================
    # DELETE TARGET
    # =====================================================

    def delete(
        self,
        request: Request,
        public_id,
        target_id,
    ):

        meeting = self.get_meeting(
            request=request,
            public_id=public_id,
        )

        self.require_management_access(
            meeting=meeting,
            membership=request.membership,
        )

        target = self.get_target(
            meeting=meeting,
            target_id=target_id,
        )

        MeetingTargetService.delete_target(
            target=target,
        )

        return ApiResponse.success(
            message="Target deleted.",
        )