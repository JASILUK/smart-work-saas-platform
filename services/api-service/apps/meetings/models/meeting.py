import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class Meeting(TimeStampedModel):

    # =====================================================
    # CATEGORY
    # =====================================================

    class Category(models.TextChoices):

        GENERAL = "general", "General"

        INTERVIEW = "interview", "Interview"

        TRAINING = "training", "Training"

        TOWNHALL = "townhall", "Townhall"

        PROJECT = "project", "Project"

    # =====================================================
    # VISIBILITY
    # =====================================================

    class Visibility(models.TextChoices):

        PRIVATE = "private", "Private"

        TARGETED = "targeted", "Targeted"

        ORGANIZATION = "organization", "Organization"

        PUBLIC = "public", "Public"

    # =====================================================
    # SCHEDULE TYPE
    # =====================================================

    class ScheduleType(models.TextChoices):

        INSTANT = "instant", "Instant"

        SCHEDULED = "scheduled", "Scheduled"

        RECURRING = "recurring", "Recurring"

    # =====================================================
    # STATUS
    # =====================================================

    class Status(models.TextChoices):

        DRAFT = "draft", "Draft"

        SCHEDULED = "scheduled", "Scheduled"

        LIVE = "live", "Live"

        COMPLETED = "completed", "Completed"

        CANCELLED = "cancelled", "Cancelled"

    # =====================================================
    # IDENTIFIERS
    # =====================================================

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    # =====================================================
    # RELATIONS
    # =====================================================

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="meetings",
    )

    created_by_membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.PROTECT,
        related_name="created_meetings",
    )

    # =====================================================
    # CORE
    # =====================================================

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    agenda = models.TextField(
        blank=True,
        default="",
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
    )

    visibility = models.CharField(
        max_length=30,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )

    schedule_type = models.CharField(
        max_length=30,
        choices=ScheduleType.choices,
        default=ScheduleType.SCHEDULED,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # =====================================================
    # TIME
    # =====================================================

    scheduled_start = models.DateTimeField()

    scheduled_end = models.DateTimeField()

    timezone = models.CharField(
        max_length=100,
        default="UTC",
    )

    recurrence_rule = models.JSONField(
        null=True,
        blank=True,
    )



    reminder_minutes = models.JSONField(
        default=list,
        blank=True,
    )

    # =====================================================
    # PARTICIPATION
    # =====================================================

    max_participants = models.PositiveIntegerField(
        default=100,
    )

    waiting_room_enabled = models.BooleanField(
        default=False,
    )

    recording_enabled = models.BooleanField(
        default=False,
    )

    # =====================================================
    # LIFECYCLE
    # =====================================================

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_meetings",
    )

    cancel_reason = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # EXTERNAL
    # =====================================================

    external_meeting_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    provider_metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:

        ordering = [
            "-scheduled_start",
        ]

        indexes = [

            models.Index(
                fields=["company"],
            ),

            models.Index(
                fields=["visibility"],
            ),

            models.Index(
                fields=["status"],
            ),

            models.Index(
                fields=["scheduled_start"],
            ),
        ]

    def __str__(self):

        return self.title





class MeetingTarget(TimeStampedModel):

    class TargetType(models.TextChoices):

        DEPARTMENT = "department", "Department"

        PROJECT = "project", "Project"

        TEAM = "team", "Team"

    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="targets",
    )

    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
    )

    target_id = models.PositiveBigIntegerField()

    created_by_membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.PROTECT,
    )

    class Meta:

        indexes = [

            models.Index(
                fields=["meeting"],
            ),

            models.Index(
                fields=["target_type"],
            ),

            models.Index(
                fields=["target_id"],
            ),
        ]