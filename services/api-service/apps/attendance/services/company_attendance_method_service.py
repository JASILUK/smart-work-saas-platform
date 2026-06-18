from typing import List, Collection, Optional
from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.selectors.company_attendance_method_selector import CompanyAttendanceMethodSelector


class CompanyAttendanceMethodService:
    """
    Coordinates data transaction lifecycles for multi-tenant logging infrastructure.
    Guarantees atomic, idempotent mutations across organizational runtime environments.
    """

    @classmethod
    @transaction.atomic
    def enable_method(cls, *, company: Company, method: str, actor: Optional[Membership]) -> CompanyAttendanceMethod:
        """
        Enables an ingestion method parameter choice idempotently.
        Re-activates a disabled instance if it already exists in the database.
        """
        config = CompanyAttendanceMethodSelector.get_company_method(company=company, method=method)

        if config:
            if not config.is_active:
                config.is_active = True
                config.created_by = actor
                config.save(update_fields=["is_active", "created_by", "updated_at"])
            return config

        return CompanyAttendanceMethod.objects.create(
            company=company,
            method=method,
            is_active=True,
            created_by=actor
        )

    @classmethod
    @transaction.atomic
    def disable_method(cls, *, company: Company, method: str, actor: Optional[Membership]) -> Optional[CompanyAttendanceMethod]:
        """
        Disables an interface option softly without executing hard database purges.
        """
        config = CompanyAttendanceMethodSelector.get_company_method(company=company, method=method)
        if config and config.is_active:
            config.is_active = False
            config.created_by = actor
            config.save(update_fields=["is_active", "created_by", "updated_at"])
        return config

    @classmethod
    @transaction.atomic
    def replace_methods(
        cls, *, company: Company, methods: Collection[str], actor: Optional[Membership]
    ) -> List[CompanyAttendanceMethod]:
        """
        Synchronizes the tenant configuration matrix with an incoming tracking state payload.
        Ensures existing options are retained, new options are mapped, and obsolete entries are deactivated.
        """
        # Clean inputs to prevent mapping empty whitespace fragments into parameter checks
        normalized_methods = {m.upper().strip() for m in methods if m and m.strip()}
        
        # Pull all existing model records inside the current tenant scope context
        existing_records = CompanyAttendanceMethod.objects.filter(company=company)
        existing_map = {rec.method: rec for rec in existing_records}

        # 1. Soft-deactivate entries omitted from incoming tracking arrays
        methods_to_deactivate = set(existing_map.keys()) - normalized_methods
        for m in methods_to_deactivate:
            rec = existing_map[m]
            if rec.is_active:
                rec.is_active = False
                rec.created_by = actor
                rec.save(update_fields=["is_active", "created_by", "updated_at"])

        # 2. Activate or initialize target entries included in the request payload
        for m in normalized_methods:
            if m in existing_map:
                rec = existing_map[m]
                if not rec.is_active:
                    rec.is_active = True
                    rec.created_by = actor
                    rec.save(update_fields=["is_active", "created_by", "updated_at"])
            else:
                CompanyAttendanceMethod.objects.create(
                    company=company,
                    method=m,
                    is_active=True,
                    created_by=actor
                )

        return list(CompanyAttendanceMethodSelector.get_company_methods(company=company))