from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company


class PolicyTypeChoices(models.TextChoices):
    SELF_ONLY = "SELF_ONLY", _("Employee Self Enrollment Only (Auto-Approve)")
    HR_ONLY = "HR_ONLY", _("HR Restricted Enrollment Only")
    SELF_WITH_APPROVAL = "SELF_WITH_APPROVAL", _("Employee Self Enrollment with HR Approval Required")


class CompanyFaceEnrollmentPolicy(TimeStampedModel):
    """
    Establishes global operational guardrails for biometrics face registration lifecycle profiles 
    scoped to specific tenant company workspaces.
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="face_enrollment_policy",
        verbose_name=_("Company Workspace Scope")
    )
    policy_type = models.CharField(
        max_length=30,
        choices=PolicyTypeChoices.choices,
        default=PolicyTypeChoices.SELF_WITH_APPROVAL,
        verbose_name=_("Biometric Policy Strategy Type")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Operational Verification Flag")
    )

    class Meta:
        db_table = "attendance_company_face_policies"
        verbose_name = _("Company Face Enrollment Policy")
        verbose_name_plural = _("Company Face Enrollment Policies")

    def __str__(self) -> str:
        return f"{self.company.name} - Face Policy ({self.get_policy_type_display()})"