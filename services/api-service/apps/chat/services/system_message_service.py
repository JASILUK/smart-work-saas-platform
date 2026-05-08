from apps.chat.models import Message


class SystemMessageService:

    @staticmethod
    def create_member_added_event(
        *,
        conversation,
        actor,
        target,
    ):

        return Message.objects.create(
            conversation=conversation,

            sender=None,

            message_type=Message.MessageType.SYSTEM,

            system_event_type=(
                Message.SystemEventType.MEMBER_ADDED
            ),

            content=(
                f"{actor.user.username} added "
                f"{target.user.username}"
            ),

            metadata={
                "actor_membership_id": actor.id,
                "target_membership_id": target.id,

                # IMPORTANT
                "target_name": (
                    target.user.username
                ),
            }
        )

    @staticmethod
    def create_member_removed_event(
        *,
        conversation,
        actor,
        target,
    ):

        return Message.objects.create(
            conversation=conversation,

            sender=None,

            message_type=Message.MessageType.SYSTEM,

            system_event_type=(
                Message.SystemEventType.MEMBER_REMOVED
            ),

            content=(
                f"{actor.user.username} removed "
                f"{target.user.username}"
            ),

            metadata={
                "actor_membership_id": actor.id,
                "target_membership_id": target.id,

                "target_name": (
                    target.user.username
                ),
            }
        )

    @staticmethod
    def create_member_left_event(
        *,
        conversation,
        membership,
    ):

        return Message.objects.create(
            conversation=conversation,

            sender=None,

            message_type=Message.MessageType.SYSTEM,

            system_event_type=(
                Message.SystemEventType.MEMBER_LEFT
            ),

            content=(
                f"{membership.user.username} left"
            ),

            metadata={
                "membership_id": membership.id,

                "name": (
                    membership.user.username
                ),
            }
        )