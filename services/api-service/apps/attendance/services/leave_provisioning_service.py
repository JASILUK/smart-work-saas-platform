import logging
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.companies.models import Company, Membership
from apps.attendance.models.leave import LeaveType, LeaveBalance

logger = logging.getLogger(__name__)

class LeaveBalanceProvisioningService:
    """
    Dedicated enterprise service for automatically provisioning missing LeaveBalance records.
    Optimized for high-performance throughput using bulk insertions and transactional blocks.
    """

    @classmethod
    @transaction.atomic
    def provision_for_leave_type(cls, *, leave_type: LeaveType) -> int:
        """
        Triggered when a new LeaveType is introduced. Generates a starting allocation matrix 
        for every active membership profile inside the parent company workspace for the current year.
        """
        current_year = timezone.now().year
        
        # Stream active membership rows using lean values list extraction
        active_memberships = Membership.objects.filter(
            company=leave_type.company,
            is_active=True
        ).values_list("id", flat=True)

        if not active_memberships:
            return 0

        quota = Decimal(str(leave_type.annual_quota))
        balances_to_create = [
            LeaveBalance(
                company=leave_type.company,
                membership_id=membership_id,
                leave_type=leave_type,
                leave_year=current_year,
                allocated_days=quota,
                used_days=Decimal("0.0"),
                remaining_days=quota
            )
            # Generator list matching active target profiles
            for membership_id in active_memberships
        ]

        # Use database unique constraint thresholds to skip pre-existing rows atomically
        inserted = LeaveBalance.objects.bulk_create(
            balances_to_create,
            ignore_conflicts=True
        )
        return len(inserted)

    @classmethod
    @transaction.atomic
    def provision_for_membership(cls, *, membership: Membership) -> int:
        """
        Triggered when a new employee joins the company. Provisions allocation cards
        for all active leave types currently configured under the target workspace tenant.
        """
        if not membership.is_active:
            return 0

        current_year = timezone.now().year
        
        # Extract active leave configurations matching company domain limits
        active_types = LeaveType.objects.filter(
            company=membership.company,
            is_active=True
        )

        if not active_types:
            return 0

        balances_to_create = [
            LeaveBalance(
                company=membership.company,
                membership=membership,
                leave_type=l_type,
                leave_year=current_year,
                allocated_days=Decimal(str(l_type.annual_quota)),
                used_days=Decimal("0.0"),
                remaining_days=Decimal(str(l_type.annual_quota))
            )
            for l_type in active_types
        ]

        inserted = LeaveBalance.objects.bulk_create(
            balances_to_create,
            ignore_conflicts=True
        )
        return len(inserted)

    @classmethod
    @transaction.atomic
    def provision_company_for_year(cls, *, company: Company, leave_year: int) -> int:
        """
        Pre-allocates ledger structures to prepare a company for an upcoming operational accounting year.
        """
        active_types = LeaveType.objects.filter(company=company, is_active=True)
        active_membership_ids = Membership.objects.filter(company=company, is_active=True).values_list("id", flat=True)

        if not active_types or not active_membership_ids:
            return 0

        balances_to_create = []
        for l_type in active_types:
            quota = Decimal(str(l_type.annual_quota))
            for m_id in active_membership_ids:
                balances_to_create.append(
                    LeaveBalance(
                        company=company,
                        membership_id=m_id,
                        leave_type=l_type,
                        leave_year=leave_year,
                        allocated_days=quota,
                        used_days=Decimal("0.0"),
                        remaining_days=quota
                    )
                )

        inserted = LeaveBalance.objects.bulk_create(
            balances_to_create,
            ignore_conflicts=True
        )
        return len(inserted)