from apps.meetings.integrations.rtc.livekit.parser import LiveKitWebhookParser
from apps.meetings.integrations.rtc.livekit.webhook import LiveKitWebhookManager
from apps.meetings.services.rtc_event_service import RTCEventService
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api_response import (
    ApiResponse,
)

from apps.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)

from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.meetings.selectors.meeting_selectors import (
    MeetingSelector,
)

from apps.meetings.selectors.session_selectors import (
    MeetingSessionSelector,
)

from apps.meetings.services.session_service import (
    MeetingSessionService,
)

from apps.meetings.api.v1.serializers.session_serializer import (
    MeetingSessionDetailSerializer,
    MeetingSessionRTCResponseSerializer,
    StartMeetingSessionSerializer,
)


# =========================================================
# BASE MIXIN
# =========================================================

class MeetingSessionAccessMixin:

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


# =========================================================
# SESSION DETAIL
# =========================================================

class MeetingSessionDetailAPI(
    MeetingSessionAccessMixin,
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

        session = (

            MeetingSessionSelector
            .get_session(
                meeting=meeting,
            )
        )

        serializer = (

            MeetingSessionDetailSerializer(
                session,
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )


# =========================================================
# START SESSION
# =========================================================

class StartMeetingSessionAPI(
    MeetingSessionAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

        "POST": "tenant.meeting.update",
    }

    # =====================================================
    # START
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

        serializer = (

            StartMeetingSessionSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        result = (

            MeetingSessionService
            .start_session(

                meeting=meeting,

                actor=request.membership,
            )
        )

        response_serializer = (

            MeetingSessionRTCResponseSerializer(
                result,
            )
        )

        return ApiResponse.success(

            data=response_serializer.data,

            message="Meeting session started.",
        )


# =========================================================
# JOIN SESSION
# =========================================================

class JoinMeetingSessionAPI(
    MeetingSessionAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

        "POST": "tenant.meeting.view",
    }

    # =====================================================
    # JOIN
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

        result = (

            MeetingSessionService
            .join_session(

                meeting=meeting,

                membership=request.membership,
            )
        )

        response_serializer = (

            MeetingSessionRTCResponseSerializer(
                result,
            )
        )

        return ApiResponse.success(

            data=response_serializer.data,

            message="Meeting joined.",
        )


# =========================================================
# LEAVE SESSION
# =========================================================

class LeaveMeetingSessionAPI(
    MeetingSessionAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

        "POST": "tenant.meeting.view",
    }

    # =====================================================
    # LEAVE
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

        MeetingSessionService.leave_session(

            meeting=meeting,

            membership=request.membership,
        )

        return ApiResponse.success(
            message="Meeting left.",
        )


# =========================================================
# END SESSION
# =========================================================

class EndMeetingSessionAPI(
    MeetingSessionAccessMixin,
    BaseCompanyAPIView,
):

    required_permissions = {

        "POST": "tenant.meeting.update",
    }

    # =====================================================
    # END
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

        session = (

            MeetingSessionService
            .end_session(

                meeting=meeting,

                actor=request.membership,
            )
        )

        response_serializer = (

            MeetingSessionDetailSerializer(
                session,
            )
        )

        return ApiResponse.success(

            data=response_serializer.data,

            message="Meeting session ended.",
        )
    





class LiveKitWebhookAPI(APIView):

    authentication_classes = []

    permission_classes = []

    # =====================================================
    # WEBHOOK
    # =====================================================

    def post(
        self,
        request,
    ):

        authorization = request.headers.get(
            "Authorization",
        )

        provider_event = (

            LiveKitWebhookManager
            .parse_event(

                body=request.body,

                authorization=authorization,
            )
        )

        rtc_event = (

            LiveKitWebhookParser
            .parse(
                event=provider_event,
            )
        )

        RTCEventService.handle_event(
            rtc_event=rtc_event,
        )

        return ApiResponse()