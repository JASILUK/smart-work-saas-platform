from typing import Optional

from rest_framework.exceptions import ValidationError, PermissionDenied
import datetime
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance

class HRFoundationValidator:
    """
    Validates structural business rules and invariant constraints.
    Keeps API views thin by keeping verification logic outside of controllers.
    """

    @staticmethod
    def validate_company_context(company: Optional[Company]) -> Company:
        if not company:
            raise PermissionDenied("Multi-tenant company context is missing or unresolved.")
        return company

    @staticmethod
    def validate_administrative_actor(user, company: Company) -> Membership:
        """
        Verifies that the acting user has a valid corporate administrative profile.
        """
        actor = Membership.objects.filter(user=user, company=company, is_active=True).first()
        if not actor:
            raise PermissionDenied("No active membership profile matches this token.")
        
        # Enforce corporate access control roles
        if not (actor.is_owner or actor.is_admin or user.is_staff):
            raise PermissionDenied("Administrative credentials are required to complete this action.")
        return actor

    @staticmethod
    def validate_target_employee(membership_id: int, company: Company) -> Membership:
        employee = Membership.objects.filter(id=membership_id, company=company).first()
        if not employee:
            raise ValidationError("The requested employee membership record does not exist within this company.")
        return employee

    @staticmethod
    def validate_operation_date(target_date: datetime.date) -> None:
        if target_date > timezone.now().date():
            raise ValidationError("Operational parameters cannot be applied to future calendar dates.")

    @staticmethod
    def validate_record_operational_state(record: Optional[DailyAttendance]) -> DailyAttendance:
        if not record:
            raise ValidationError("The requested daily attendance record was not found.")
        return record