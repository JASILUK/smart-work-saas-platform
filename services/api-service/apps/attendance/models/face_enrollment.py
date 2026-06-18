from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership


class EnrollmentStatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Awaiting HR Verification Review")
    APPROVED = "APPROVED", _("Active and Allowed for Verification Sign-ins")
    REJECTED = "REJECTED", _("Enrollment Denied by Administrator")
    REVOKED = "REVOKED", _("Previously Active Profile Explicitly Deactivated")


class EnrollmentSourceChoices(models.TextChoices):
    EMPLOYEE = "EMPLOYEE", _("Employee Self Service Registration")
    HR = "HR", _("HR Administrator Initiated Assignment")


class FaceEnrollment(TimeStampedModel):
    """
    Retains immutable historical records and math vector hashes used to authenticate 
    identity verifications across connected check-in interfaces.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="face_enrollments",
        verbose_name=_("Company Context")
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="face_enrollments",
        verbose_name=_("Employee Profile Context")
    )
    status = models.CharField(
        max_length=15,
        choices=EnrollmentStatusChoices.choices,
        default=EnrollmentStatusChoices.PENDING,
        verbose_name=_("Verification Status State"),
        db_index=True
    )
    enrollment_source = models.CharField(
        max_length=15,
        choices=EnrollmentSourceChoices.choices,
        verbose_name=_("Enrollment Registration Origin")
    )
    embedding = models.JSONField(
        verbose_name=_("Math Matrix Feature Vector Embeddings Array Hash"),
        help_text=_("Stores mathematical float structures capturing biometric attributes. Image data is discarded.")
    )
    embedding_version = models.CharField(
        max_length=50,
        default="v1.0.0",
        verbose_name=_("Model Architecture Ingestion Version Name")
    )
    similarity_threshold = models.FloatField(
        default=0.85,
        verbose_name=_("Minimum Cosine Passing Vector Confidence Limit")
    )
    liveness_verified = models.BooleanField(
        default=False,
        verbose_name=_("Anti-Spoofing Liveness Verification Status Check Passed")
    )
    
    # Audit trail trackers mapping structural modifications
    approved_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_face_enrollments",
        verbose_name=_("Approving Administrator Context")
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Approval Execution Timestamp")
    )
    rejection_reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Administrative Rejection Narrative Explanation")
    )
    revoked_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_face_enrollments",
        verbose_name=_("Revoking Administrator Context")
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Revocation Execution Timestamp")
    )
    revocation_reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Administrative Revocation Narrative Explanation")
    )

    class Meta:
        db_table = "attendance_face_enrollments"
        ordering = ["-created_at"]
        verbose_name = _("Biometric Face Profile Enrollment")
        verbose_name_plural = _("Biometric Face Profile Enrollments")

    def __str__(self) -> str:
        return f"{self.membership.user.username} - Face Enrollment ({self.status})"