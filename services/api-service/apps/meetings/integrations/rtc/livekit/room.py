import asyncio

from django.conf import settings

from livekit import api


class LiveKitRoomManager:

    # =====================================================
    # CREATE ROOM
    # =====================================================

    @staticmethod
    def create_room(
        *,
        room_name,
    ):

        async def _create():

            client = api.LiveKitAPI(

                settings.LIVEKIT_URL,

                settings.LIVEKIT_API_KEY,

                settings.LIVEKIT_API_SECRET,
            )

            room = await (

                client.room.create_room(

                    api.CreateRoomRequest(
                        name=room_name,
                    )
                )
            )

            return {
                "rtc_room_id": room.sid,
                "room_name": room.name,
            }

        return asyncio.run(
            _create()
        )

    # =====================================================
    # DELETE ROOM
    # =====================================================

    @staticmethod
    def delete_room(
        *,
        room_name,
    ):

        async def _delete():

            client = api.LiveKitAPI(

                settings.LIVEKIT_URL,

                settings.LIVEKIT_API_KEY,

                settings.LIVEKIT_API_SECRET,
            )

            await (

                client.room.delete_room(

                    api.DeleteRoomRequest(
                        room=room_name,
                    )
                )
            )

            return True

        return asyncio.run(
            _delete()
        )