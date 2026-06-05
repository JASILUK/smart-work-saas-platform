from asgiref.sync import async_to_sync

from channels.layers import (
    get_channel_layer,
)


class MeetingRealtimeService:

    @classmethod
    def broadcast_participant_joined(
        cls,
        *,
        tenant_id,
        meeting_id,
        participant,
    ):

        channel_layer = (
            get_channel_layer()
        )

        payload = {
            "membership_id": (
                participant["membership_id"]
            ),

            "username": (
                participant["username"]
            ),

            "role": (
                participant["role"]
            ),
        }

        async_to_sync(
            channel_layer.group_send
        )(
            cls.get_meeting_group_name(
                tenant_id=tenant_id,
                meeting_id=meeting_id,
            ),
            {
                "type": (
                    "participant_joined"
                ),

                "meeting_id": str(
                    meeting_id
                ),

                "participant": payload,
            }
        )

    # =====================================================
    # PARTICIPANT LEFT
    # =====================================================

    @classmethod
    def broadcast_participant_left(
        cls,
        *,
        tenant_id,
        meeting_id,
        membership_id,
    ):

        channel_layer = (
            get_channel_layer()
        )

        async_to_sync(
            channel_layer.group_send
        )(
            cls.get_meeting_group_name(
                tenant_id=tenant_id,
                meeting_id=meeting_id,
            ),
            {
                "type": (
                    "participant_left"
                ),

                "meeting_id": str(
                    meeting_id
                ),

                "membership_id": (
                    membership_id
                ),
            }
        )

    # =====================================================
    # MEETING ENDED
    # =====================================================

    @classmethod
    def broadcast_meeting_ended(
        cls,
        *,
        tenant_id,
        meeting_id,
    ):

        channel_layer = (
            get_channel_layer()
        )

        async_to_sync(
            channel_layer.group_send
        )(
            cls.get_meeting_group_name(
                tenant_id=tenant_id,
                meeting_id=meeting_id,
            ),
            {
                "type": (
                    "meeting_ended"
                ),

                "meeting_id": str(
                    meeting_id
                ),
            }
        )