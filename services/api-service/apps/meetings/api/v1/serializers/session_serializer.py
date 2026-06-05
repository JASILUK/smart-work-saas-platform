from rest_framework import serializers

from apps.meetings.models.session import (
    MeetingSession,
)


# =========================================================
# SESSION DETAIL
# =========================================================

class MeetingSessionDetailSerializer(
    serializers.ModelSerializer
):

    meeting_public_id = serializers.UUIDField(
        source="meeting.public_id",
        read_only=True,
    )

    meeting_title = serializers.CharField(
        source="meeting.title",
        read_only=True,
    )

    started_by = serializers.SerializerMethodField()

    ended_by = serializers.SerializerMethodField()

    class Meta:

        model = MeetingSession

        fields = [
            "id",
            "meeting_public_id",
            "meeting_title",
            "session_status",
            "rtc_provider",
            "rtc_room_id",
            "recording_enabled",
            "recording_url",
            "peak_participant_count",
            "started_by",
            "ended_by",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
        ]

    # =====================================================
    # STARTED BY
    # =====================================================

    def get_started_by(
        self,
        obj,
    ):

        if not obj.started_by:
            return None

        return {
            "id": obj.started_by.id,
            "username": (
                obj.started_by.user.username
            ),
        }

    # =====================================================
    # ENDED BY
    # =====================================================

    def get_ended_by(
        self,
        obj,
    ):

        if not obj.ended_by:
            return None

        return {
            "id": obj.ended_by.id,
            "username": (
                obj.ended_by.user.username
            ),
        }


# =========================================================
# RTC CONNECTION
# =========================================================

class RTCConnectionSerializer(
    serializers.Serializer
):

    room_name = serializers.CharField()

    rtc_provider = serializers.CharField()

    ws_url = serializers.CharField()

    token = serializers.CharField()


# =========================================================
# SESSION RTC RESPONSE
# =========================================================

class MeetingSessionRTCResponseSerializer(
    serializers.Serializer
):

    session = (
        MeetingSessionDetailSerializer()
    )

    rtc = (
        RTCConnectionSerializer()
    )


# =========================================================
# START SESSION
# =========================================================

class StartMeetingSessionSerializer(
    serializers.Serializer
):

    recording_enabled = serializers.BooleanField(
        required=False,
        default=False,
    )


# =========================================================
# END SESSION
# =========================================================

class EndMeetingSessionSerializer(
    serializers.Serializer
):

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )