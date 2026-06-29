# =====================================================
# SERVICES
# =====================================================
# apps/leave/services.py
# =====================================================

import datetime
from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone
from apps.companies.models import Membership
from apps.attendance.models.leave import LeaveType, LeaveBalance, LeaveRequest
from apps.attendance.selectors.leave_selector import LeaveTypeSelector, LeaveBalanceSelector, LeaveRequestSelector
from apps.attendance.validators.leave_validator import (
    LeaveTypeValidator,
    LeaveBalanceValidator,
    LeaveRequestValidator,
)


class LeaveTypeService:
    """
    Business logic for LeaveType write operations.
    """

    @classmethod
    def create(
        cls,
        *,
        company,
        name: str,
        code: str,
        description: str = "",
        annual_quota: int = 0,
        is_paid: bool = True,
        requires_approval: bool = True,
        allow_half_day: bool = True,
        requires_attachment: bool = False,
    ) -> LeaveType:
        LeaveTypeValidator.validate_unique_code(code=code, company=company)

        leave_type = LeaveType.objects.create(
            company=company,
            name=name,
            code=code,
            description=description,
            annual_quota=annual_quota,
            is_paid=is_paid,
            requires_approval=requires_approval,
            allow_half_day=allow_half_day,
            requires_attachment=requires_attachment,
        )

        from apps.attendance.services.leave_provisioning_service import LeaveBalanceProvisioningService
        LeaveBalanceProvisioningService.provision_for_leave_type(leave_type=leave_type)
        
        return leave_type

    @classmethod
    def update(
        cls,
        *,
        leave_type: LeaveType,
        name: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        annual_quota: Optional[int] = None,
        is_paid: Optional[bool] = None,
        requires_approval: Optional[bool] = None,
        allow_half_day: Optional[bool] = None,
        requires_attachment: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> LeaveType:
        if code is not None and code != leave_type.code:
            LeaveTypeValidator.validate_unique_code(
                code=code,
                company=leave_type.company,
                exclude_id=leave_type.id,
            )
            leave_type.code = code

        if name is not None:
            leave_type.name = name
        if description is not None:
            leave_type.description = description
        if annual_quota is not None:
            leave_type.annual_quota = annual_quota
        if is_paid is not None:
            leave_type.is_paid = is_paid
        if requires_approval is not None:
            leave_type.requires_approval = requires_approval
        if allow_half_day is not None:
            leave_type.allow_half_day = allow_half_day
        if requires_attachment is not None:
            leave_type.requires_attachment = requires_attachment
        if is_active is not None:
            leave_type.is_active = is_active

        leave_type.save()
        return leave_type

    @classmethod
    def deactivate(cls, *, leave_type: LeaveType) -> LeaveType:
        leave_type.is_active = False
        leave_type.save(update_fields=["is_active", "updated_at"])
        return leave_type


class LeaveBalanceService:
    """
    Business logic for LeaveBalance write operations.
    """

    @classmethod
    def yearly_allocation(
        cls,
        *,
        company,
        membership: Membership,
        leave_type: LeaveType,
        leave_year: int,
        allocated_days: Decimal,
    ) -> LeaveBalance:
        LeaveBalanceValidator.validate_year(year=leave_year)

        balance, created = LeaveBalance.objects.get_or_create(
            company=company,
            membership=membership,
            leave_type=leave_type,
            leave_year=leave_year,
            defaults={
                "allocated_days": allocated_days,
                "used_days": Decimal("0.0"),
                "remaining_days": allocated_days,
            },
        )

        if not created:
            balance.allocated_days = allocated_days
            balance.remaining_days = allocated_days - balance.used_days
            balance.save(update_fields=["allocated_days", "remaining_days", "updated_at"])

        return balance

    @classmethod
    def manual_adjustment(
        cls,
        *,
        balance: LeaveBalance,
        adjustment_days: Decimal,
        reason: str = "",
    ) -> LeaveBalance:
        LeaveBalanceValidator.validate_adjustment_amount(amount=adjustment_days)

        with transaction.atomic():
            # Lock the balance row
            locked_balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)

            new_remaining = locked_balance.remaining_days + adjustment_days
            if new_remaining < 0:
                LeaveBalanceValidator.validate_negative_balance_protection(
                    balance=locked_balance,
                    deduction=abs(adjustment_days),
                )

            locked_balance.remaining_days = new_remaining
            locked_balance.allocated_days += adjustment_days
            locked_balance.save(update_fields=["allocated_days", "remaining_days", "updated_at"])

        return locked_balance

    @classmethod
    def consume_balance(
        cls,
        *,
        balance: LeaveBalance,
        days: Decimal,
    ) -> LeaveBalance:
        LeaveBalanceValidator.validate_negative_balance_protection(
            balance=balance,
            deduction=days,
        )

        with transaction.atomic():
            locked_balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
            locked_balance.used_days += days
            locked_balance.remaining_days -= days
            locked_balance.save(update_fields=["used_days", "remaining_days", "updated_at"])

        return locked_balance

    @classmethod
    def restore_balance(
        cls,
        *,
        balance: LeaveBalance,
        days: Decimal,
    ) -> LeaveBalance:
        with transaction.atomic():
            locked_balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
            locked_balance.used_days -= days
            locked_balance.remaining_days += days
            locked_balance.save(update_fields=["used_days", "remaining_days", "updated_at"])

        return locked_balance


class LeaveRequestService:
    """
    Business logic for LeaveRequest write operations.
    """

    @classmethod
    def _calculate_total_days(
        cls,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
        is_half_day: bool,
    ) -> Decimal:
        if is_half_day:
            return Decimal("0.5")
        delta = (end_date - start_date).days + 1
        return Decimal(str(delta))

    @classmethod
    def create_request(
        cls,
        *,
        company,
        membership: Membership,
        leave_type_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
        is_half_day: bool = False,
        half_day_session: str = "",
        reason: str = "",
        attachment: Optional = None,
    ) -> LeaveRequest:
        LeaveRequestValidator.validate_employee_active(membership=membership)

        leave_type = LeaveTypeSelector.get_by_id(
            leave_type_id=leave_type_id,
            company=company,
        )
        if not leave_type:
            raise ValueError("Leave type not found.")

        LeaveRequestValidator.validate_leave_type_active(leave_type=leave_type)
        LeaveRequestValidator.validate_leave_type_company(
            leave_type=leave_type,
            company=company,
        )
        LeaveRequestValidator.validate_attachment_required(
            leave_type=leave_type,
            attachment=attachment,
        )
        LeaveRequestValidator.validate_half_day_allowed(
            leave_type=leave_type,
            is_half_day=is_half_day,
        )
        LeaveRequestValidator.validate_date_range(
            start_date=start_date,
            end_date=end_date,
        )
        LeaveRequestValidator.validate_no_invalid_ranges(
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_session=half_day_session,
        )
        LeaveRequestValidator.validate_overlapping_requests(
            membership=membership,
            start_date=start_date,
            end_date=end_date,
        )

        total_days = cls._calculate_total_days(
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
        )

        balance = LeaveRequestValidator.validate_enough_balance(
            membership=membership,
            leave_type=leave_type,
            start_date=start_date,
            total_days=total_days,
        )

        with transaction.atomic():
            leave_request = LeaveRequest.objects.create(
                company=company,
                membership=membership,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                total_days=total_days,
                is_half_day=is_half_day,
                half_day_session=half_day_session if is_half_day else "",
                reason=reason,
                attachment=attachment,
                status=LeaveRequest.Status.PENDING,
            )

            # If no approval required, auto-approve and consume
            if not leave_type.requires_approval:
                leave_request.status = LeaveRequest.Status.APPROVED
                leave_request.approved_by = None
                leave_request.approved_at = timezone.now()
                leave_request.save(update_fields=["status", "approved_by", "approved_at"])

                LeaveBalanceService.consume_balance(
                    balance=balance,
                    days=total_days,
                )

        return leave_request

    @classmethod
    def cancel_request(
        cls,
        *,
        leave_request: LeaveRequest,
        canceller: Membership,
    ) -> LeaveRequest:
        LeaveRequestValidator.validate_cancel_rules(
            leave_request=leave_request,
            canceller=canceller,
            is_hr=False,
        )

        with transaction.atomic():
            if leave_request.status == LeaveRequest.Status.APPROVED:
                # Restore balance for approved requests
                balance = LeaveBalanceSelector.get_by_membership_and_type(
                    membership=leave_request.membership,
                    leave_type=leave_request.leave_type,
                    leave_year=leave_request.start_date.year,
                )
                if balance:
                    LeaveBalanceService.restore_balance(
                        balance=balance,
                        days=leave_request.total_days,
                    )

            leave_request.status = LeaveRequest.Status.CANCELLED
            leave_request.save(update_fields=["status", "updated_at"])

        return leave_request

    @classmethod
    def approve_request(
        cls,
        *,
        leave_request: LeaveRequest,
        approver: Membership,
    ) -> LeaveRequest:
        LeaveRequestValidator.validate_approve_rules(
            leave_request=leave_request,
            approver=approver,
        )

        total_days = leave_request.total_days

        with transaction.atomic():
            # Lock balance
            balance = LeaveBalanceSelector.get_by_membership_and_type(
                membership=leave_request.membership,
                leave_type=leave_request.leave_type,
                leave_year=leave_request.start_date.year,
            )

            if not balance:
                raise ValueError("Leave balance not found.")

            LeaveBalanceValidator.validate_negative_balance_protection(
                balance=balance,
                deduction=total_days,
            )

            # Deduct balance
            LeaveBalanceService.consume_balance(
                balance=balance,
                days=total_days,
            )

            # Approve request
            leave_request.status = LeaveRequest.Status.APPROVED
            leave_request.approved_by = approver
            leave_request.approved_at = timezone.now()
            leave_request.save(update_fields=["status", "approved_by", "approved_at"])

        return leave_request

    @classmethod
    def reject_request(
        cls,
        *,
        leave_request: LeaveRequest,
        rejector: Membership,
        rejection_reason: str,
    ) -> LeaveRequest:
        LeaveRequestValidator.validate_reject_rules(
            leave_request=leave_request,
            rejector=rejector,
        )

        # Reject must never change balance
        leave_request.status = LeaveRequest.Status.REJECTED
        leave_request.rejection_reason = rejection_reason
        leave_request.save(update_fields=["status", "rejection_reason", "updated_at"])

        return leave_request

    @classmethod
    def hr_cancel_request(
        cls,
        *,
        leave_request: LeaveRequest,
        canceller: Membership,
    ) -> LeaveRequest:
        LeaveRequestValidator.validate_cancel_rules(
            leave_request=leave_request,
            canceller=canceller,
            is_hr=True,
        )

        with transaction.atomic():
            if leave_request.status == LeaveRequest.Status.APPROVED:
                # Restore balance for approved requests
                balance = LeaveBalanceSelector.get_by_membership_and_type(
                    membership=leave_request.membership,
                    leave_type=leave_request.leave_type,
                    leave_year=leave_request.start_date.year,
                )
                if balance:
                    LeaveBalanceService.restore_balance(
                        balance=balance,
                        days=leave_request.total_days,
                    )

            leave_request.status = LeaveRequest.Status.CANCELLED
            leave_request.save(update_fields=["status", "updated_at"])

        return leave_request
