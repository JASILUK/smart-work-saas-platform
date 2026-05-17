# apps/companies/services/department_application_service.py

from django.db import transaction

from apps.chat.services.department_chat_service import (
    DepartmentChatService,
)

from apps.companies.services.DepartmentService import (
    DepartmentService,
)

from apps.companies.services.department_membership_service import (
    DepartmentMembershipService,
)


class DepartmentApplicationService:

    # =====================================================
    # CREATE DEPARTMENT WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_department(
        *,
        company,
        created_by,
        name,
        parent=None,
        head=None,
        description=None,
    ):

        # =================================================
        # CREATE DEPARTMENT
        # =================================================

        department = (
            DepartmentService.create(

                company=company,

                name=name,

                parent=parent,

                head=head,

                description=description,
            )
        )

        # =================================================
        # CREATE DEPARTMENT CHAT
        # =================================================

        DepartmentChatService.create_department_conversation(

            department=department,

            created_by=created_by,
        )

        return department

    # =====================================================
    # UPDATE DEPARTMENT WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_department(
        *,
        department,
        name=None,
        parent=None,
        head=None,
        description=None,
    ):

        updated_department = (
            DepartmentService.update(

                department=department,

                name=name,

                parent=parent,

                head=head,

                description=description,
            )
        )

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=updated_department,
            )
        )

        # =================================================
        # SYNC CHAT INFO
        # =================================================

        if conversation:

            DepartmentChatService.sync_department_conversation_info(
                department=updated_department,
            )

            DepartmentChatService.sync_department_head(
                department=updated_department,
            )

        return updated_department

    # =====================================================
    # DELETE DEPARTMENT WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def delete_department(
        *,
        department,
    ):

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        # =================================================
        # ARCHIVE CHAT
        # =================================================

        if conversation:

            DepartmentChatService.archive_department_conversation(
                department=department,
            )

        # =================================================
        # DELETE DEPARTMENT
        # =================================================

        DepartmentService.delete(
            department=department,
        )

        return True

    # =====================================================
    # ASSIGN MEMBER WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_member(
        *,
        department,
        membership,
    ):

        updated_membership = (
            DepartmentMembershipService.assign_member(

                department=department,

                membership=membership,
            )
        )

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        # =================================================
        # ADD MEMBER TO CHAT
        # =================================================

        if conversation:

            DepartmentChatService.add_member_to_chat(

                department=department,

                membership=membership,
            )

        return updated_membership

    # =====================================================
    # BULK ASSIGN MEMBERS WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def bulk_assign_members(
        *,
        department,
        memberships,
    ):

        updated_memberships = (
            DepartmentMembershipService
            .bulk_assign_members(
                department=department,
                memberships=memberships,
            )
        )

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        # =================================================
        # ADD MEMBERS TO CHAT
        # =================================================

        if conversation:

            for membership in memberships:

                DepartmentChatService.add_member_to_chat(

                    department=department,

                    membership=membership,
                )

        return updated_memberships

    # =====================================================
    # REMOVE MEMBER WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def remove_member(
        *,
        department,
        membership,
    ):

        updated_membership = (
            DepartmentMembershipService.remove_member(

                department=department,

                membership=membership,
            )
        )

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        # =================================================
        # REMOVE MEMBER FROM CHAT
        # =================================================

        if conversation:

            DepartmentChatService.remove_member_from_chat(

                department=department,

                membership=membership,
            )

        return updated_membership

    # =====================================================
    # TRANSFER MEMBER WORKFLOW
    # =====================================================

    @staticmethod
    @transaction.atomic
    def transfer_member(
        *,
        membership,
        from_department,
        to_department,
    ):

        # =================================================
        # OLD CHAT
        # REMOVE BEFORE TRANSFER
        # =================================================

        old_conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=from_department,
            )
        )

        if old_conversation:

            DepartmentChatService.remove_member_from_chat(

                department=from_department,

                membership=membership,
            )

        # =================================================
        # TRANSFER MEMBERSHIP
        # =================================================

        updated_membership = (
            DepartmentMembershipService.transfer_member(

                membership=membership,

                from_department=from_department,

                to_department=to_department,
            )
        )

        # =================================================
        # NEW CHAT
        # =================================================

        new_conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=to_department,
            )
        )

        if new_conversation:

            DepartmentChatService.add_member_to_chat(

                department=to_department,

                membership=membership,
            )

        # =================================================
        # SYNC HEAD ROLES
        # =================================================

        if old_conversation:

            DepartmentChatService.sync_department_head(
                department=from_department,
            )

        if new_conversation:

            DepartmentChatService.sync_department_head(
                department=to_department,
            )

        return updated_membership

    # =====================================================
    # ASSIGN DEPARTMENT HEAD
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_department_head(
        *,
        department,
        membership,
    ):

        updated_department = (
            DepartmentService.assign_head(

                department=department,

                membership=membership,
            )
        )

        # =================================================
        # GET CHAT
        # =================================================

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        # =================================================
        # SYNC CHAT ADMIN ROLE
        # =================================================

        if conversation:

            DepartmentChatService.sync_department_head(
                department=department,
            )

        return updated_department