from apps.meetings.integrations.rtc.factory import (
    RTCProviderFactory,
)


class RTCService:

    # =====================================================
    # CREATE ROOM
    # =====================================================

    @staticmethod
    def create_room(
        *,
        session,
    ):

        provider = (

            RTCProviderFactory
            .get_provider(
                session.rtc_provider
            )
        )

        room_data = provider.create_room(

            room_name=(
                f"meeting-{session.meeting.public_id}"
            )
        )

        session.rtc_room_id = (
            room_data.get(
                "rtc_room_id"
            )
        )

        session.save(
            update_fields=[
                "rtc_room_id",
                "updated_at",
            ]
        )

        return session

    # =====================================================
    # DELETE ROOM
    # =====================================================

    @staticmethod
    def delete_room(
        *,
        session,
    ):

        provider = (

            RTCProviderFactory
            .get_provider(
                session.rtc_provider
            )
        )

        provider.delete_room(

            room_name=(
                f"meeting-{session.meeting.public_id}"
            )
        )

    # =====================================================
    # GENERATE TOKEN
    # =====================================================

    @staticmethod
    def generate_token(
        *,
        session,
        membership,
    ):

        provider = (

            RTCProviderFactory
            .get_provider(
                session.rtc_provider
            )
        )

        return provider.generate_token(

            room_name=(
                f"meeting-{session.meeting.public_id}"
            ),

            participant_identity=(
                str(membership.id)
            ),

            participant_name=(
                membership.user.username
            ),

            metadata={
                "membership_id": (
                    membership.id
                )
            },
        )