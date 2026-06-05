from apps.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)

from apps.meetings.api.v1.serializers.meeting_serializer import (
    MeetingDetailSerializer,
    MeetingTargetOutputSerializer,
)

from apps.meetings.selectors.meeting_selectors import (
    MeetingSelector,
)

from apps.meetings.selectors.target_selectors import (
    MeetingTargetSelector,
)


class MeetingAccessMixin:

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

        can_access = (

            MeetingSelector
            .can_access_meeting(
                meeting=meeting,
                membership=request.membership,
            )
        )

        if not can_access:

            raise PermissionDeniedError(
                message=(
                    "You do not have access "
                    "to this meeting."
                )
            )

        return meeting

    # =====================================================
    # REQUIRE MANAGEMENT ACCESS
    # =====================================================

    def require_management_access(
        self,
        *,
        meeting,
        membership,
    ):

        can_manage = (

            MeetingSelector
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

    # =====================================================
    # GET TARGET
    # =====================================================

    def get_target(
        self,
        *,
        meeting,
        target_id,
    ):

        target = (

            MeetingTargetSelector
            .get_target(
                meeting=meeting,
                target_id=target_id,
            )
        )

        if not target:

            raise NotFoundError(
                message="Target not found."
            )

        return target

    # =====================================================
    # SERIALIZE MEETING
    # =====================================================

    def serialize_meeting(
        self,
        *,
        request,
        meeting,
    ):

        target_map = (

            MeetingTargetSelector
            .build_target_map(
                meeting=meeting,
            )
        )

        return (

            MeetingDetailSerializer(

                meeting,

                context={

                    "request": request,

                    "target_map": target_map,
                },
            ).data
        )

    # =====================================================
    # SERIALIZE TARGET
    # =====================================================

    def serialize_target(
        self,
        *,
        meeting,
        target,
    ):

        target_map = (

            MeetingTargetSelector
            .build_target_map(
                meeting=meeting,
            )
        )

        return (

            MeetingTargetOutputSerializer(

                target,

                context={
                    "target_map": target_map,
                },
            ).data
        )

    # =====================================================
    # SERIALIZE TARGET LIST
    # =====================================================

    def serialize_targets(
        self,
        *,
        meeting,
        targets,
    ):

        target_map = (

            MeetingTargetSelector
            .build_target_map(
                meeting=meeting,
            )
        )

        return (

            MeetingTargetOutputSerializer(

                targets,

                many=True,

                context={
                    "target_map": target_map,
                },
            ).data
        )