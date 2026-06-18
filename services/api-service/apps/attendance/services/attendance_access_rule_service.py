from typing import List
from django.db import transaction
from apps.companies.models import Company
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule
from apps.attendance.validators.attendance_access_validator import AttendanceAccessValidator


class AttendanceAccessRuleService:
    """
    Handles transactions for grouped conditional access rules.
    """
    @classmethod
    @transaction.atomic
    def create_rule(cls, *, company: Company, validated_data: dict) -> AttendanceAccessRule:
        method_ids = [m.id for m in validated_data.pop("allowed_methods", [])]
        location_ids = [l.id for l in validated_data.pop("allowed_locations", [])]

        AttendanceAccessRuleValidator.validate_method_and_locations(method_ids, location_ids, company)

        rule = AttendanceAccessRule(company=company, **validated_data)
        if rule.is_active:
            AttendanceAccessValidator.validate_rule_constraints(rule, method_ids, location_ids)
        rule.save()

        rule.allowed_methods.set(method_ids)
        rule.allowed_locations.set(location_ids)
        return rule

    @classmethod
    @transaction.atomic
    def update_rule(cls, *, instance: AttendanceAccessRule, validated_data: dict) -> AttendanceAccessRule:
        method_objs = validated_data.pop("allowed_methods", None)
        location_objs = validated_data.pop("allowed_locations", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        m_ids = [m.id for m in method_objs] if method_objs is not None else list(instance.allowed_methods.values_list("id", flat=True))
        l_ids = [l.id for l in location_objs] if location_objs is not None else list(instance.allowed_locations.values_list("id", flat=True))

        AttendanceAccessValidator.validate_method_and_locations(m_ids, l_ids, instance.company)
        if instance.is_active:
            AttendanceAccessValidator.validate_rule_constraints(instance, m_ids, l_ids)

        instance.save()
        if method_objs is not None:
            instance.allowed_methods.set(method_objs)
        if location_objs is not None:
            instance.allowed_locations.set(location_objs)

        return instance