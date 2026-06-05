from django.conf import settings

from apps.meetings.integrations.rtc.livekit.room import (
    LiveKitRoomManager,
)

from apps.meetings.integrations.rtc.livekit.token import (
    LiveKitTokenManager,
)


class LiveKitRTCProvider:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.ws_url = (
            settings.LIVEKIT_URL
        )

        self.room_manager = (
            LiveKitRoomManager()
        )

        self.token_manager = (
            LiveKitTokenManager()
        )

    # =====================================================
    # CREATE ROOM
    # =====================================================

    def create_room(
        self,
        *,
        room_name,
    ):

        return (

            self.room_manager
            .create_room(
                room_name=room_name,
            )
        )

    # =====================================================
    # DELETE ROOM
    # =====================================================

    def delete_room(
        self,
        *,
        room_name,
    ):

        return (

            self.room_manager
            .delete_room(
                room_name=room_name,
            )
        )

    # =====================================================
    # GENERATE TOKEN
    # =====================================================

    def generate_token(
        self,
        *,
        room_name,
        participant_identity,
        participant_name,
    ):

        return (

            self.token_manager
            .generate_token(

                room_name=room_name,

                participant_identity=(
                    participant_identity
                ),

                participant_name=(
                    participant_name
                ),
            )
        )