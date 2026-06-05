from dataclasses import dataclass


@dataclass
class RTCWebhookEvent:

    event_type: str

    room_id: str

    participant_identity: str | None = None

    metadata: dict | None = None