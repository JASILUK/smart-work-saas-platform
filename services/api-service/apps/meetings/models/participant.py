from django.db import models

from apps.core.models import TimeStampedModel


class MeetingParticipant(TimeStampedModel):

    # =====================================================
    # PARTICIPANT ROLE
    # =====================================================

    class Role(models.TextChoices):

        HOST = "host", "Host"
        CO_HOST = "co_host", "Co Host"
        PARTICIPANT = "participant", "Participant"
        VIEWER = "viewer", "Viewer"

    # =====================================================
    # INVITATION / ATTENDANCE STATUS
    # =====================================================

    class Status(models.TextChoices):

        INVITED = "invited", "Invited"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        JOINED = "joined", "Joined"
        LEFT = "left", "Left"
        NO_SHOW = "no_show", "No Show"

    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="participants",
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="meeting_participations",
    )

    invited_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_meeting_invitations",
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.INVITED,
    )

    invited_at = models.DateTimeField(
        auto_now_add=True,
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    joined_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    left_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attendance_duration_seconds = models.PositiveIntegerField(
        default=0,
    )

    joined_count = models.PositiveIntegerField(
        default=0,
    )

    is_present = models.BooleanField(
        default=False,
    )

    can_invite = models.BooleanField(
        default=False,
    )

    can_moderate = models.BooleanField(
        default=False,
    )

    last_joined_at = models.DateTimeField(
    null=True,
    blank=True,
)

    attendance_percentage = models.FloatField(
        default=0,
    )

    attendance_status = models.CharField(
        max_length=30,
        default="absent",
    )

    class Meta:

        unique_together = [
            ("meeting", "membership"),
        ]

        indexes = [
            models.Index(fields=["meeting"]),
            models.Index(fields=["membership"]),
            models.Index(fields=["status"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_present"]),
        ]

    def __str__(self):

        return (
            f"{self.membership} - "
            f"{self.meeting}"
        )