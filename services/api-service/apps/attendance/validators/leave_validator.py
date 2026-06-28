# =====================================================
# VALIDATORS
# =====================================================
# apps/leave/validators.py
# =====================================================

import datetime
from decimal import Decimal
from typing import Optional
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.companies.models import Membership
from apps.attendance.models.leave import LeaveType, LeaveBalance, LeaveRequest
from apps.attendance.selectors.leave_selector import LeaveTypeSelector, LeaveBalanceSelector, LeaveRequestSelector


class LeaveTypeValidator:
    """
    Domain validators for LeaveType operations.
    """

    @classmethod
    def validate_unique_code(
        cls,
        *,
        code: str,
        company,
        exclude_id: Optional[int] = None,
    ) -> None:
        queryset = LeaveType.objects.filter(code__iexact=code, company=company)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        if queryset.exists():
            raise ValidationError(
                {"code": f"Leave type with code '{code}' already exists for this company."}
            )

    @classmethod
    def validate_active(cls, *, leave_type: LeaveType) -> None:
        if not leave_type.is_active:
            raise ValidationError(
                {"leave_type": "The selected leave type is inactive."}
            )

    @classmethod
    def validate_belongs_to_company(
        cls,
        *,
        leave_type: LeaveType,
        company,
    ) -> None:
        if leave_type.company_id != company.id:
            raise ValidationError(
                {"leave_type": "Leave type does not belong to this company."}
            )


class LeaveBalanceValidator:
    """
    Domain validators for LeaveBalance operations.
    """

    @classmethod
    def validate_adjustment_amount(cls, *, amount: Decimal) -> None:
        if amount == 0:
            raise ValidationError(
                {"amount": "Adjustment amount cannot be zero."}
            )

    @classmethod
    def validate_negative_balance_protection(
        cls,
        *,
        balance: LeaveBalance,
        deduction: Decimal,
    ) -> None:
        new_remaining = balance.remaining_days - deduction
        if new_remaining < 0:
            raise ValidationError(
                {"balance": f"Insufficient balance. Available: {balance.remaining_days}, Required: {deduction}"}
            )

    @classmethod
    def validate_year(cls, *, year: int) -> None:
        current_year = timezone.now().year
        if year < current_year - 1 or year > current_year + 1:
            raise ValidationError(
                {"leave_year": f"Invalid leave year. Must be between {current_year - 1} and {current_year + 1}."}
            )

    @classmethod
    def validate_balance_exists(
        cls,
        *,
        membership: Membership,
        leave_type: LeaveType,
        leave_year: int,
    ) -> LeaveBalance:
        balance = LeaveBalanceSelector.get_by_membership_and_type(
            membership=membership,
            leave_type=leave_type,
            leave_year=leave_year,
        )
        if not balance:
            raise ValidationError(
                {"balance": f"No leave balance found for {leave_type.name} in year {leave_year}."}
            )
        return balance


class LeaveRequestValidator:
    """
    Domain validators for LeaveRequest operations.
    """

    @classmethod
    def validate_employee_active(cls, *, membership: Membership) -> None:
        if not membership.is_active:
            raise ValidationError(
                {"membership": "Employee membership is not active."}
            )

    @classmethod
    def validate_leave_type_active(cls, *, leave_type: LeaveType) -> None:
        LeaveTypeValidator.validate_active(leave_type=leave_type)

    @classmethod
    def validate_leave_type_company(
        cls,
        *,
        leave_type: LeaveType,
        company,
    ) -> None:
        LeaveTypeValidator.validate_belongs_to_company(
            leave_type=leave_type,
            company=company,
        )

    @classmethod
    def validate_attachment_required(
        cls,
        *,
        leave_type: LeaveType,
        attachment: Optional,
    ) -> None:
        if leave_type.requires_attachment and not attachment:
            raise ValidationError(
                {"attachment": f"Attachment is required for {leave_type.name} leave requests."}
            )

    @classmethod
    def validate_half_day_allowed(
        cls,
        *,
        leave_type: LeaveType,
        is_half_day: bool,
    ) -> None:
        if is_half_day and not leave_type.allow_half_day:
            raise ValidationError(
                {"is_half_day": f"Half-day requests are not allowed for {leave_type.name}."}
            )

    @classmethod
    def validate_date_range(
        cls,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> None:
        if start_date > end_date:
            raise ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        if start_date < timezone.now().date():
            raise ValidationError(
                {"start_date": "Start date cannot be in the past."}
            )

    @classmethod
    def validate_no_invalid_ranges(
        cls,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
        is_half_day: bool,
        half_day_session: str,
    ) -> None:
        if is_half_day:
            if start_date != end_date:
                raise ValidationError(
                    {"is_half_day": "Half-day requests must have the same start and end date."}
                )
            if not half_day_session:
                raise ValidationError(
                    {"half_day_session": "Half-day session is required for half-day requests."}
                )

    @classmethod
    def validate_overlapping_requests(
        cls,
        *,
        membership: Membership,
        start_date: datetime.date,
        end_date: datetime.date,
        exclude_id: Optional[int] = None,
    ) -> None:
        overlapping = LeaveRequestSelector.get_overlapping_requests(
            membership=membership,
            start_date=start_date,
            end_date=end_date,
            exclude_id=exclude_id,
        )
        if overlapping.exists():
            raise ValidationError(
                {"date_range": "This date range overlaps with an existing leave request."}
            )

    @classmethod
    def validate_enough_balance(
        cls,
        *,
        membership: Membership,
        leave_type: LeaveType,
        start_date: datetime.date,
        total_days: Decimal,
    ) -> LeaveBalance:
        leave_year = start_date.year
        balance = LeaveBalanceSelector.get_by_membership_and_type(
            membership=membership,
            leave_type=leave_type,
            leave_year=leave_year,
        )
        if not balance:
            raise ValidationError(
                {"balance": f"No leave balance available for {leave_type.name} in {leave_year}."}
            )
        if balance.remaining_days < total_days:
            raise ValidationError(
                {
                    "balance": (
                        f"Insufficient balance for {leave_type.name}. "
                        f"Available: {balance.remaining_days}, Requested: {total_days}"
                    )
                }
            )
        return balance

    @classmethod
    def validate_pending_state_transition(cls, *, leave_request: LeaveRequest) -> None:
        if leave_request.status != LeaveRequest.Status.PENDING:
            raise ValidationError(
                {"status": f"Request must be pending to perform this action. Current status: {leave_request.status}"}
            )

    @classmethod
    def validate_approve_rules(
        cls,
        *,
        leave_request: LeaveRequest,
        approver: Membership,
    ) -> None:
        if leave_request.status != LeaveRequest.Status.PENDING:
            raise ValidationError(
                {"status": "Only pending requests can be approved."}
            )
        if leave_request.membership_id == approver.id:
            raise ValidationError(
                {"approver": "You cannot approve your own leave request."}
            )

    @classmethod
    def validate_reject_rules(
        cls,
        *,
        leave_request: LeaveRequest,
        rejector: Membership,
    ) -> None:
        if leave_request.status != LeaveRequest.Status.PENDING:
            raise ValidationError(
                {"status": "Only pending requests can be rejected."}
            )
        if leave_request.membership_id == rejector.id:
            raise ValidationError(
                {"rejector": "You cannot reject your own leave request."}
            )

    @classmethod
    def validate_cancel_rules(
        cls,
        *,
        leave_request: LeaveRequest,
        canceller: Membership,
        is_hr: bool = False,
    ) -> None:
        if leave_request.status == LeaveRequest.Status.CANCELLED:
            raise ValidationError(
                {"status": "Request is already cancelled."}
            )
        if not is_hr and leave_request.membership_id != canceller.id:
            raise ValidationError(
                {"canceller": "You can only cancel your own leave requests."}
            )
        if leave_request.status == LeaveRequest.Status.REJECTED:
            raise ValidationError(
                {"status": "Rejected requests cannot be cancelled."}
            )

    @classmethod
    def validate_company_isolation(
        cls,
        *,
        leave_request: LeaveRequest,
        company,
    ) -> None:
        if leave_request.company_id != company.id:
            raise ValidationError(
                {"company": "Leave request does not belong to this company."}
            )

