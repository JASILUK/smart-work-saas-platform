# apps/chat/services/department_chat_service.py

from django.db import transaction

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
)

from apps.companies.models import (
    Department,
    Membership,
)

from apps.core.exceptions import ValidationError


class DepartmentChatService:

    # =====================================================
    # CREATE DEPARTMENT CONVERSATION
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_department_conversation(
        *,
        department: Department,
        created_by,
    ):

        existing_conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if existing_conversation:
            return existing_conversation

        # =================================================
        # CREATE CONVERSATION
        # =================================================

        conversation = Conversation.objects.create(

            company=department.company,

            type=Conversation.Type.DEPARTMENT,

            name=department.name,

            description=department.description,

            is_system_managed=True,

            created_by=created_by,
        )

        # =================================================
        # LINK DEPARTMENT
        # =================================================

        department.conversation = conversation

        department.save(
            update_fields=[
                "conversation",
                "updated_at",
            ]
        )

        # =================================================
        # SYNC MEMBERS
        # =================================================

        DepartmentChatService.sync_department_members(
            department=department,
        )

        # =================================================
        # SYNC HEAD ROLE
        # =================================================

        DepartmentChatService.sync_department_head(
            department=department,
        )

        return conversation

    # =====================================================
    # GET DEPARTMENT CONVERSATION
    # =====================================================

    @staticmethod
    def get_department_conversation(
        *,
        department: Department,
    ):

        return department.conversation

    # =====================================================
    # SYNC ALL MEMBERS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def sync_department_members(
        *,
        department: Department,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:

            raise ValidationError(
                "Department conversation not found"
            )

        memberships = (
            Membership.objects
            .filter(
                department=department,
                is_active=True,
            )
            .select_related("user")
        )

        existing_member_ids = set(

            ConversationParticipant.objects
            .filter(
                conversation=conversation,
            )
            .values_list(
                "membership_id",
                flat=True,
            )
        )

        participants_to_create = []

        for membership in memberships:

            if membership.id in existing_member_ids:
                continue

            role = (
                ConversationParticipant.Role.ADMIN
                if department.head_id == membership.id
                else ConversationParticipant.Role.MEMBER
            )

            participants_to_create.append(

                ConversationParticipant(
                    conversation=conversation,
                    membership=membership,
                    chat_role=role,
                )
            )

        if participants_to_create:

            ConversationParticipant.objects.bulk_create(
                participants_to_create,
            )

        # =================================================
        # REMOVE INVALID PARTICIPANTS
        # =================================================

        valid_member_ids = set(
            memberships.values_list(
                "id",
                flat=True,
            )
        )

        ConversationParticipant.objects.filter(
            conversation=conversation,
        ).exclude(
            membership_id__in=valid_member_ids,
        ).delete()

        return True

    # =====================================================
    # ADD MEMBER TO CHAT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def add_member_to_chat(
        *,
        department: Department,
        membership: Membership,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:

            raise ValidationError(
                "Department conversation not found"
            )

        if membership.department_id != department.id:

            raise ValidationError(
                "Membership does not belong to department"
            )

        role = (
            ConversationParticipant.Role.ADMIN
            if department.head_id == membership.id
            else ConversationParticipant.Role.MEMBER
        )

        participant, created = (
            ConversationParticipant.objects.get_or_create(

                conversation=conversation,

                membership=membership,

                defaults={
                    "chat_role": role,
                },
            )
        )

        if (
            not created
            and
            participant.chat_role != role
        ):

            participant.chat_role = role

            participant.save(
                update_fields=[
                    "chat_role",
                    "updated_at",
                ]
            )

        return participant

    # =====================================================
    # REMOVE MEMBER FROM CHAT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def remove_member_from_chat(
        *,
        department: Department,
        membership: Membership,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:
            return True

        ConversationParticipant.objects.filter(
            conversation=conversation,
            membership=membership,
        ).delete()

        return True

    # =====================================================
    # SYNC DEPARTMENT HEAD
    # =====================================================

    @staticmethod
    @transaction.atomic
    def sync_department_head(
        *,
        department: Department,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:

            raise ValidationError(
                "Department conversation not found"
            )

        # =================================================
        # RESET ADMINS
        # =================================================

        ConversationParticipant.objects.filter(
            conversation=conversation,
            chat_role=ConversationParticipant.Role.ADMIN,
        ).update(
            chat_role=ConversationParticipant.Role.MEMBER,
        )

        # =================================================
        # NO HEAD
        # =================================================

        if not department.head_id:
            return True

        participant, _ = (
            ConversationParticipant.objects.get_or_create(

                conversation=conversation,

                membership=department.head,

                defaults={
                    "chat_role": (
                        ConversationParticipant.Role.ADMIN
                    ),
                },
            )
        )

        if (
            participant.chat_role !=
            ConversationParticipant.Role.ADMIN
        ):

            participant.chat_role = (
                ConversationParticipant.Role.ADMIN
            )

            participant.save(
                update_fields=[
                    "chat_role",
                    "updated_at",
                ]
            )

        return True

    # =====================================================
    # SYNC CONVERSATION INFO
    # =====================================================

    @staticmethod
    @transaction.atomic
    def sync_department_conversation_info(
        *,
        department: Department,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:

            raise ValidationError(
                "Department conversation not found"
            )

        conversation.name = department.name

        conversation.description = (
            department.description
        )

        conversation.save(
            update_fields=[
                "name",
                "description",
                "updated_at",
            ]
        )

        return conversation

    # =====================================================
    # ARCHIVE DEPARTMENT CHAT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def archive_department_conversation(
        *,
        department: Department,
    ):

        conversation = (
            DepartmentChatService
            .get_department_conversation(
                department=department,
            )
        )

        if not conversation:
            return True

        ConversationParticipant.objects.filter(
            conversation=conversation,
        ).delete()

        conversation.name = (
            f"[ARCHIVED] {conversation.name}"
        )

        conversation.save(
            update_fields=[
                "name",
                "updated_at",
            ]
        )

        return conversation