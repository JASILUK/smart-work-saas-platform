# apps/chat/services/group_service.py

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
)
from apps.chat.services.group_realtime_service import GroupRealtimeService
from apps.chat.services.message_service import MessageService
from apps.chat.services.system_message_service import SystemMessageService
from apps.core.exceptions import ApplicationError
from apps.core.media_storage_service import upload_file


class GroupService:

    # =========================================================
    # CREATE GROUP
    # =========================================================
    @staticmethod
    @transaction.atomic
    def create_group(
        *,
        creator_membership,
        name,
        member_ids=None,
        avatar=None,
        description=None,
    ):

        member_ids = member_ids or []

        name = (name or "").strip()

        if not name:
            raise ApplicationError("Group name required")

        avatar_url = None

        if avatar:

            upload_result = upload_file(
                avatar,
                folder="group_avatars",
            )

            avatar_url = upload_result["url"]

        conversation = Conversation.objects.create(
            company=creator_membership.company,
            type=Conversation.Type.GROUP,
            name=name,
            avatar=avatar_url,
            description=description,
            created_by=creator_membership.user,
        )

        participants = [
            ConversationParticipant(
                conversation=conversation,
                membership=creator_membership,
                chat_role=ConversationParticipant.Role.OWNER,
            )
        ]

        unique_member_ids = set(member_ids)

        for member_id in unique_member_ids:

            if member_id == creator_membership.id:
                continue

            participants.append(
                ConversationParticipant(
                    conversation=conversation,
                    membership_id=member_id,
                    chat_role=ConversationParticipant.Role.MEMBER,
                )
            )

        ConversationParticipant.objects.bulk_create(
            participants
        )

        conversation = (
            Conversation.objects
            .prefetch_related(
                "participants",
                "participants__membership",
                "participants__membership__user",
            )
            .get(id=conversation.id)
        )

        # ==========================================
        # REALTIME BROADCAST
        # ==========================================
        GroupRealtimeService.broadcast_conversation_created(
            conversation=conversation,
        )

        return conversation

    # =========================================================
    # ADD MEMBERS
    # =========================================================
    @staticmethod
    @transaction.atomic
    def add_members(
        *,
        conversation_id,
        actor_membership,
        member_ids,
    ):

        conversation = GroupService._get_group_conversation(
            conversation_id
        )

        GroupService._ensure_not_department_conversation(
            conversation
        )

        GroupService._ensure_admin_or_owner(
            conversation_id,
            actor_membership,
        )

        existing_ids = set(
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).values_list("membership_id", flat=True)
        )

        participants = []

        for member_id in set(member_ids):

            if member_id in existing_ids:
                continue

            participants.append(
                ConversationParticipant(
                    conversation=conversation,
                    membership_id=member_id,
                    chat_role=ConversationParticipant.Role.MEMBER,
                )
            )

        created_participants = (
            ConversationParticipant.objects.bulk_create(
                participants
            )
        )

        

        # ==========================================
        # SYSTEM EVENTS
        # ==========================================
        for participant in created_participants:

            system_message = (
                SystemMessageService.create_member_added_event(
                    conversation=conversation,
                    actor=actor_membership,
                    target=participant.membership,
                )
            )

            MessageService.broadcast_system_message(
                system_message
            )

        # ==========================================
        # SEND CONVERSATION TO NEW MEMBERS
        # ==========================================
        conversation.refresh_from_db()

        GroupRealtimeService.broadcast_conversation_created(
            conversation=conversation,
        )

        return True

    # =========================================================
    # REMOVE MEMBER
    # =========================================================
    @staticmethod
    @transaction.atomic
    def remove_member(
        *,
        conversation_id,
        actor_membership,
        target_membership_id,
    ):

        conversation = GroupService._get_group_conversation(
            conversation_id
        )

        GroupService._ensure_not_department_conversation(
            conversation
        )

        GroupService._ensure_admin_or_owner(
            conversation_id,
            actor_membership,
        )

        if actor_membership.id == target_membership_id:
            raise ApplicationError(
                "Use leave group endpoint"
            )

        participant = get_object_or_404(
            ConversationParticipant,
            conversation=conversation,
            membership_id=target_membership_id,
        )

        if (
            participant.chat_role ==
            ConversationParticipant.Role.OWNER
        ):
            owner_count = (
                ConversationParticipant.objects.filter(
                    conversation=conversation,
                    chat_role=ConversationParticipant.Role.OWNER,
                ).count()
            )

            if owner_count <= 1:
                raise ApplicationError(
                    "Cannot remove last owner"
                )


        target_membership = participant.membership

        participant.delete()

        system_message = (
            SystemMessageService.create_member_removed_event(
                conversation=conversation,
                actor=actor_membership,
                target=target_membership,
            )
        )

        MessageService.broadcast_system_message(
            system_message
        )

        return True

    # =========================================================
    # LEAVE GROUP
    # =========================================================
    @staticmethod
    @transaction.atomic
    def leave_group(
        *,
        conversation_id,
        membership,
    ):

        conversation = GroupService._get_group_conversation(
            conversation_id
        )

        GroupService._ensure_not_department_conversation(
            conversation
        )

        participant = get_object_or_404(
            ConversationParticipant,
            conversation=conversation,
            membership=membership,
        )

        if (
            participant.chat_role ==
            ConversationParticipant.Role.OWNER
        ):
            owner_count = (
                ConversationParticipant.objects.filter(
                    conversation=conversation,
                    chat_role=ConversationParticipant.Role.OWNER,
                ).count()
            )

            if owner_count <= 1:
                raise ApplicationError(
                    "Transfer ownership before leaving"
                )

        
        left_membership = participant.membership

        participant.delete()

        system_message = (
            SystemMessageService.create_member_left_event(
                conversation=conversation,
                membership=left_membership,
            )
        )

        MessageService.broadcast_system_message(
            system_message
        )

        return True

    # =========================================================
    # UPDATE ROLE
    # =========================================================
    @staticmethod
    @transaction.atomic
    def update_role(
        *,
        conversation_id,
        actor_membership,
        target_membership_id,
        role,
    ):

        valid_roles = [
            ConversationParticipant.Role.OWNER,
            ConversationParticipant.Role.ADMIN,
            ConversationParticipant.Role.MEMBER,
        ]

        if role not in valid_roles:
            raise ApplicationError("Invalid role")

        conversation = GroupService._get_group_conversation(
            conversation_id
        )
    
        GroupService._ensure_not_department_conversation(
            conversation
        )

        actor = GroupService._get_participant(
            conversation_id,
            actor_membership.id,
        )

        target = GroupService._get_participant(
            conversation_id,
            target_membership_id,
        )

        if (
            target.chat_role ==
            ConversationParticipant.Role.OWNER
            and
            actor.chat_role !=
            ConversationParticipant.Role.OWNER
        ):
            raise ApplicationError(
                "Only owner can modify owner role"
            )

        if (
            target.chat_role ==
            ConversationParticipant.Role.OWNER
            and
            role != ConversationParticipant.Role.OWNER
        ):
            owner_count = (
                ConversationParticipant.objects.filter(
                    conversation=conversation,
                    chat_role=ConversationParticipant.Role.OWNER,
                ).count()
            )

            if owner_count <= 1:
                raise ApplicationError(
                    "Cannot remove last owner"
                )

        target.chat_role = role
        target.save(update_fields=["chat_role"])

        return target

    # =========================================================
    # UPDATE GROUP
    # =========================================================
    @staticmethod
    @transaction.atomic
    def update_group(
        *,
        conversation_id,
        actor_membership,
        name=None,
        avatar=None,
        description=None,
        ):

        conversation = GroupService._get_group_conversation(
            conversation_id
        )
        
        GroupService._ensure_not_department_conversation(
            conversation
        )
        GroupService._ensure_admin_or_owner(
            conversation_id,
            actor_membership,
        )

        # -----------------------------------------
        # NAME
        # -----------------------------------------
        if name is not None:

            cleaned_name = name.strip()

            if not cleaned_name:
                raise ApplicationError(
                    "Group name cannot be empty"
                )

            conversation.name = cleaned_name

        # -----------------------------------------
        # DESCRIPTION
        # -----------------------------------------
        if description is not None:

            conversation.description = description.strip()

        # -----------------------------------------
        # AVATAR UPLOAD
        # -----------------------------------------
        if avatar:

            upload_result = upload_file(
                avatar,
                folder="group_avatars",
            )

            conversation.avatar = upload_result["url"]

        conversation.save(
            update_fields=[
                "name",
                "description",
                "avatar",
                "updated_at",
            ]
        )

        return conversation

    # =========================================================
    # GET GROUP DETAILS
    # =========================================================
    @staticmethod
    def get_group_details(
        *,
        conversation_id,
        membership,
    ):

        GroupService._ensure_member(
            conversation_id,
            membership,
        )

        return (
            Conversation.objects
            .select_related("company")
            .prefetch_related(
                "participants",
                "participants__membership",
                "participants__membership__user",
            )
            .get(id=conversation_id)
        )

    # =========================================================
    # INTERNALS
    # =========================================================
    @staticmethod
    def _get_group_conversation(conversation_id):

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
        )

        if conversation.type not in [
            Conversation.Type.GROUP,
            Conversation.Type.DEPARTMENT,
        ]:
            raise ApplicationError(
                "Invalid conversation type"
            )

        return conversation

    @staticmethod
    def _get_participant(
        conversation_id,
        membership_id,
    ):
        return get_object_or_404(
            ConversationParticipant,
            conversation_id=conversation_id,
            membership_id=membership_id,
        )

    @staticmethod
    def _ensure_member(
        conversation_id,
        membership,
    ):

        exists = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership,
        ).exists()

        if not exists:
            raise ApplicationError("Access denied")

    @staticmethod
    def _ensure_admin_or_owner(
        conversation_id,
        membership,
    ):

        exists = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership,
            chat_role__in=[
                ConversationParticipant.Role.OWNER,
                ConversationParticipant.Role.ADMIN,
            ]
        ).exists()

        if not exists:
            raise ApplicationError(
                "Admin permission required"
            )
        
    @staticmethod
    def _ensure_not_department_conversation(
        conversation,
    ):

        if (
            conversation.type ==
            Conversation.Type.DEPARTMENT
        ):

            raise ApplicationError(
                "Department conversations are system managed"
            )