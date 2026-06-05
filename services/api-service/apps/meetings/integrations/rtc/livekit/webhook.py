import json

from django.conf import settings

from livekit.api import (
    TokenVerifier,
)

from livekit.protocol.webhook import (
    WebhookEvent,
)


class LiveKitWebhookManager:

    # =====================================================
    # VERIFY AND PARSE EVENT
    # =====================================================

    @staticmethod
    def parse_event(
        *,
        body,
        authorization,
    ):

        verifier = TokenVerifier(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )

        claims = verifier.verify(
            authorization,
        )

        if not claims:

            raise ValueError(
                "Invalid webhook signature."
            )

        payload = json.loads(body)

        return WebhookEvent.from_json(
            payload,
        )