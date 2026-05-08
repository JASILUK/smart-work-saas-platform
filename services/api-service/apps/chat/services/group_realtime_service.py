# apps/chat/services/group_realtime_service.py

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework.test import APIRequestFactory

from apps.chat.models import ConversationParticipant
from apps.chat.api.v1.serializers import (
    ConversationSerializer,
)


class GroupRealtimeService:

    @staticmethod
    def broadcast_conversation_created(
        *,
        conversation,
    ):

        channel_layer = get_channel_layer()

        participants = (
            ConversationParticipant.objects
            .select_related(
                "membership",
                "membership__user",
            )
            .filter(
                conversation=conversation
            )
        )

        # ==========================================
        # SEND PERSONALIZED PAYLOAD
        # ==========================================
        for participant in participants:

            # --------------------------------------
            # FAKE REQUEST CONTEXT
            # --------------------------------------
            request = APIRequestFactory().get("/")

            request.membership = (
                participant.membership
            )

            serialized = (
                ConversationSerializer(
                    conversation,
                    context={
                        "request": request
                    }
                ).data
            )

            async_to_sync(
                channel_layer.group_send
            )(
                (
                    f"tenant_"
                    f"{conversation.company_id}"
                    f"_user_"
                    f"{participant.membership_id}"
                ),
                {
                    "type": "conversation_created",

                    "conversation": serialized,
                }
            )



    