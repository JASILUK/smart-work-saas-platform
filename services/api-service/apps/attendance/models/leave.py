from django.db import models
from apps.core.models import TimeStampedModel


class LeaveType(TimeStampedModel):
    """
    Represents company leave policy configurations and entitlements.
    """

    # =====================================================
    # COMPANY / TENANCY
    # =====================================================
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="leave_types",
        verbose_name="Company",
        help_text="The tenant company owning this leave policy configuration.",
    )

    # =====================================================
    # BASIC INFORMATION
    # =====================================================
    name = models.CharField(
        max_length=100,
        verbose_name="Leave Type Name",
        help_text="The display name of the leave type (e.g., Annual Leave, Sick Leave).",
    )
    code = models.CharField(
        max_length=20,
        verbose_name="Leave Type Code",
        help_text="Unique shorthand token used for reporting and integrations (e.g., AL, SL).",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Detailed rules or context around this leave type policy.",
    )

    # =====================================================
    # POLICY CONFIGURATION
    # =====================================================
    annual_quota = models.PositiveIntegerField(
        default=0,
        verbose_name="Annual Quota",
        help_text="Standard yearly baseline allotment of days granted for this policy.",
    )
    is_paid = models.BooleanField(
        default=True,
        verbose_name="Is Paid Leave",
        help_text="Designates if taking this leave type maintains normal payroll payout cycles.",
    )
    requires_approval = models.BooleanField(
        default=True,
        verbose_name="Requires Approval",
        help_text="Specifies if requests against this type must explicitly go through an approval cycle.",
    )
    allow_half_day = models.BooleanField(
        default=True,
        verbose_name="Allow Half-Day Requests",
        help_text="Enables employees to split individual work days when registering this type.",
    )
    requires_attachment = models.BooleanField(
        default=False,
        verbose_name="Requires Attachment",
        help_text="Enables enforcement of document proofs or medical certificates on submission.",
    )

    # =====================================================
    # STATUS
    # =====================================================
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Deactivating hides this choice from users without damaging historical data bindings.",
    )

    # =====================================================
    # META
    # =====================================================
    class Meta:
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company"], name="idx_leavetype_company"),
            models.Index(fields=["is_active"], name="idx_leavetype_is_active"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uni_leavetype_company_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(TimeStampedModel):
    """
    Represents the consolidated yearly total leave tracking numbers for a given employee.
    Calculations and changes are mutated only via specialized Domain Services.
    """

    # =====================================================
    # COMPANY / TENANCY
    # =====================================================
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="leave_balances",
        verbose_name="Company",
        help_text="The tenant workspace owning this specific balance ledger context.",
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================
    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="leave_balances",
        verbose_name="Employee Membership",
        help_text="The unique company member ledger profile context mapping this balance row.",
    )
    leave_type = models.ForeignKey(
        "attendance.LeaveType",
        on_delete=models.PROTECT,
        related_name="leave_balances",
        verbose_name="Leave Type Relation",
        help_text="The specific leave type rule system defining these numbers.",
    )

    # =====================================================
    # TIME PERIOD
    # =====================================================
    leave_year = models.PositiveIntegerField(
        verbose_name="Leave Year",
        help_text="The target operational accounting year this profile tracking applies to (e.g., 2026).",
    )

    # =====================================================
    # ENTITLEMENT LEDGERS
    # =====================================================
    allocated_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        verbose_name="Allocated Days",
        help_text="Total base pool days available to this individual for the calendar year cycle.",
    )
    used_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        verbose_name="Used Days",
        help_text="Total sum count of approved utilized workflow leave days.",
    )
    remaining_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        verbose_name="Remaining Days",
        help_text="The actual net safe available entitlement days left to draw upon.",
    )

    # =====================================================
    # META
    # =====================================================
    class Meta:
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        ordering = ["-leave_year", "membership__user__last_name", "leave_type__name"]
        indexes = [
            models.Index(fields=["company"], name="idx_leavebal_company"),
            models.Index(fields=["membership"], name="idx_leavebal_membership"),
            models.Index(fields=["leave_year"], name="idx_leavebal_year"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "membership", "leave_type", "leave_year"],
                name="uni_leavebal_mbr_type_year",
            )
        ]

    def __str__(self):
        return f"{self.membership} - {self.leave_type.code} ({self.leave_year})"


class LeaveRequest(TimeStampedModel):
    """
    Tracks lifecycle historical details and approval execution steps of an employee leave petition.
    """

    # =====================================================
    # WORKFLOW ENUMS
    # =====================================================
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class HalfDaySession(models.TextChoices):
        FIRST_HALF = "first_half", "First Half"
        SECOND_HALF = "second_half", "Second Half"

    # =====================================================
    # COMPANY / TENANCY
    # =====================================================
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="leave_requests",
        verbose_name="Company",
        help_text="Multi-tenant context tracker isolating this transaction record.",
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================
    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="leave_requests",
        verbose_name="Employee Membership",
        help_text="The worker seeking leave clearance visibility context.",
    )
    leave_type = models.ForeignKey(
        "attendance.LeaveType",
        on_delete=models.PROTECT,
        related_name="leave_requests",
        verbose_name="Leave Type Rule",
        help_text="Protected baseline identity rules backing this registration data payload.",
    )

    # =====================================================
    # DATE BOUNDS & SCHEDULES
    # =====================================================
    start_date = models.DateField(
        verbose_name="Start Date",
        help_text="First localized date of absent leave timeline tracking.",
    )
    end_date = models.DateField(
        verbose_name="End Date",
        help_text="Inclusive final date bound of absent leave timeline tracking.",
    )
    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name="Total Accounted Days",
        help_text="Calculated total decimal value balance impacted by this request.",
    )

    # =====================================================
    # HALF DAY SETTINGS
    # =====================================================
    is_half_day = models.BooleanField(
        default=False,
        verbose_name="Is Half Day Request",
        help_text="Flag designating if this event counts as a sub-day partial cycle block.",
    )
    half_day_session = models.CharField(
        max_length=20,
        choices=HalfDaySession.choices,
        blank=True,
        default="",
        verbose_name="Half Day Session Choice",
        help_text="Dictates partial day distribution segment details when is_half_day evaluates true.",
    )

    # =====================================================
    # CORE REASONS / EVIDENCE ATTACHMENT
    # =====================================================
    reason = models.TextField(
        verbose_name="Reason Description",
        help_text="Explanatory text clarifying context for why the leave time is requested.",
    )
    attachment = models.FileField(
        upload_to="leave_attachments/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Evidence Document",
        help_text="Optional generic documentation or policy justification certificates uploaded by worker.",
    )

    # =====================================================
    # STATE MANAGEMENT / AUDITING
    # =====================================================
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Workflow Status",
        help_text="Current processing tracking lifecycle flag state.",
    )
    approved_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_leave_requests",
        verbose_name="Approver Membership Profile",
        help_text="The authorized actor executing state lifecycle change controls.",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Approved Timestamp",
        help_text="System clock tracking exact execution time of processing state approval mutations.",
    )
    rejection_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Rejection Context",
        help_text="Mandatory audit trail reason detail appended if status transitions to Rejected.",
    )

    # =====================================================
    # META
    # =====================================================
    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company"], name="idx_leavereq_company"),
            models.Index(fields=["membership"], name="idx_leavereq_membership"),
            models.Index(fields=["status"], name="idx_leavereq_status"),
            models.Index(fields=["start_date"], name="idx_leavereq_start_date"),
        ]

    def __str__(self):
        return f"{self.membership} - {self.leave_type.code} ({self.start_date} to {self.end_date})"