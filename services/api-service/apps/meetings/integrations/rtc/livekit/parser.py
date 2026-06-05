from apps.meetings.integrations.rtc.base_events import (
    RTCWebhookEvent,
)


class LiveKitWebhookParser:

    # =====================================================
    # PARSE EVENT
    # =====================================================

    @staticmethod
    def parse(
        *,
        event,
    ):

        participant_identity = None

        if event.participant:

            participant_identity = (
                event.participant.identity
            )

        return RTCWebhookEvent(

            event_type=event.event,

            room_id=event.room.name,

            participant_identity=(
                participant_identity
            ),

            metadata={},
        )