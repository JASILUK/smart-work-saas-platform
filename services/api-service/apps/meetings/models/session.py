from django.db import models

from apps.core.models import TimeStampedModel


class MeetingSession(TimeStampedModel):

    # =====================================================
    # SESSION STATUS
    # =====================================================

    class SessionStatus(models.TextChoices):

        WAITING = "waiting", "Waiting"

        LIVE = "live", "Live"

        ENDED = "ended", "Ended"

    # =====================================================
    # RTC PROVIDER
    # =====================================================

    class RTCProvider(models.TextChoices):

        LIVEKIT = "livekit", "LiveKit"

        AGORA = "agora", "Agora"

        JITSI = "jitsi", "Jitsi"

        DAILY = "daily", "Daily"

    # =====================================================
    # RELATIONS
    # =====================================================

    meeting = models.OneToOneField(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="session",
    )

    # =====================================================
    # RTC
    # =====================================================

    rtc_provider = models.CharField(
        max_length=30,
        choices=RTCProvider.choices,
        default=RTCProvider.LIVEKIT,
    )

    rtc_room_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    # =====================================================
    # SESSION STATE
    # =====================================================

    session_status = models.CharField(
        max_length=30,
        choices=SessionStatus.choices,
        default=SessionStatus.WAITING,
    )

    # =====================================================
    # RECORDING
    # =====================================================

    recording_enabled = models.BooleanField(
        default=False,
    )

    recording_url = models.URLField(
        null=True,
        blank=True,
    )

    # =====================================================
    # LIFECYCLE
    # =====================================================

    started_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="started_meeting_sessions",
    )

    ended_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ended_meeting_sessions",
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =====================================================
    # ANALYTICS
    # =====================================================

    peak_participant_count = models.PositiveIntegerField(
        default=0,
    )

    # =====================================================
    # EXTRA
    # =====================================================

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:

        indexes = [

            models.Index(
                fields=["session_status"],
            ),

            models.Index(
                fields=["started_at"],
            ),

            models.Index(
                fields=["rtc_provider"],
            ),
        ]

    def __str__(self):

        return (
            f"{self.meeting.title} "
            f"- {self.session_status}"
        )