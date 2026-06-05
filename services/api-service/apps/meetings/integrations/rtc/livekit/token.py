from django.conf import settings

from livekit import api


class LiveKitTokenManager:

    # =====================================================
    # GENERATE TOKEN
    # =====================================================

    @staticmethod
    def generate_token(
        *,
        room_name,
        participant_identity,
        participant_name,
        metadata=None,
    ):

        access_token = api.AccessToken(

            settings.LIVEKIT_API_KEY,

            settings.LIVEKIT_API_SECRET,
        )

        access_token.with_identity(
            participant_identity
        )

        access_token.with_name(
            participant_name
        )

        access_token.with_grants(

            api.VideoGrants(
                room_join=True,
                room=room_name,
            )
        )

        if metadata:

            access_token.with_metadata(
                str(metadata)
            )

        return {
            "token": access_token.to_jwt(),
        }