from django.db import transaction

from apps.companies.models import (
    Department,
    Membership,
)

from apps.core.exceptions import ValidationError


class DepartmentMembershipService:

    # =====================================================
    # ASSIGN MEMBER TO DEPARTMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_member(
        *,
        department: Department,
        membership: Membership,
    ):

        # =================================================
        # COMPANY VALIDATION
        # =================================================

        if (
            membership.company_id !=
            department.company_id
        ):

            raise ValidationError(
                "Membership must belong to same company"
            )

        # =================================================
        # MEMBERSHIP ACTIVE VALIDATION
        # =================================================

        if not membership.is_active:

            raise ValidationError(
                "Membership is inactive"
            )

        # =================================================
        # ALREADY ASSIGNED
        # =================================================

        if (
            membership.department_id ==
            department.id
        ):

            return membership

        # =================================================
        # ASSIGN
        # =================================================

        membership.department = department

        membership.save(
            update_fields=[
                "department",
                "updated_at",
            ]
        )

        return membership

    # =====================================================
    # REMOVE MEMBER FROM DEPARTMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def remove_member(
        *,
        department: Department,
        membership: Membership,
    ):

        # =================================================
        # VALIDATION
        # =================================================

        if (
            membership.department_id !=
            department.id
        ):

            raise ValidationError(
                "Member does not belong to department"
            )

        # =================================================
        # REMOVE HEAD
        # =================================================

        if (
            department.head_id ==
            membership.id
        ):

            department.head = None

            department.save(
                update_fields=[
                    "head",
                    "updated_at",
                ]
            )

        # =================================================
        # REMOVE DEPARTMENT
        # =================================================

        membership.department = None

        membership.save(
            update_fields=[
                "department",
                "updated_at",
            ]
        )

        return membership

    # =====================================================
    # BULK ASSIGN MEMBERS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def bulk_assign_members(
        *,
        department: Department,
        memberships,
    ):

        updated_memberships = []

        for membership in memberships:

            updated_memberships.append(

                DepartmentMembershipService
                .assign_member(
                    department=department,
                    membership=membership,
                )
            )

        return updated_memberships

    # =====================================================
    # BULK REMOVE MEMBERS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def bulk_remove_members(
        *,
        department: Department,
        memberships,
    ):

        updated_memberships = []

        for membership in memberships:

            updated_memberships.append(

                DepartmentMembershipService
                .remove_member(
                    department=department,
                    membership=membership,
                )
            )

        return updated_memberships

    # =====================================================
    # TRANSFER MEMBER
    # =====================================================

    @staticmethod
    @transaction.atomic
    def transfer_member(
        *,
        membership: Membership,
        from_department: Department,
        to_department: Department,
    ):

        # =================================================
        # VALIDATE SOURCE
        # =================================================

        if (
            membership.department_id !=
            from_department.id
        ):

            raise ValidationError(
                "Member does not belong to source department"
            )

        # =================================================
        # VALIDATE TARGET
        # =================================================

        if (
            from_department.company_id !=
            to_department.company_id
        ):

            raise ValidationError(
                "Departments must belong to same company"
            )

        # =================================================
        # REMOVE OLD HEAD
        # =================================================

        if (
            from_department.head_id ==
            membership.id
        ):

            from_department.head = None

            from_department.save(
                update_fields=[
                    "head",
                    "updated_at",
                ]
            )

        # =================================================
        # TRANSFER MEMBERSHIP
        # =================================================

        membership.department = to_department

        membership.save(
            update_fields=[
                "department",
                "updated_at",
            ]
        )

        return membership