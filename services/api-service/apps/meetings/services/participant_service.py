from django.core.exceptions import ValidationError
from django.db import transaction

from apps.companies.models import (
    Membership,
)

from apps.meetings.models.participant import (
    MeetingParticipant,
)
from apps.meetings.selectors.participant_selectors import MeetingParticipantSelector


class MeetingParticipantService:

    # =====================================================
    # CREATE HOST
    # =====================================================

    @staticmethod
    def create_host_participant(
        *,
        meeting,
        membership,
        is_instant_meeting=False,
        current_time=None,
    ):

        return MeetingParticipant.objects.create(

            meeting=meeting,

            membership=membership,

            invited_by=membership,

            role=MeetingParticipant.Role.HOST,

            status=(

                MeetingParticipant.Status.JOINED

                if is_instant_meeting

                else

                MeetingParticipant.Status.ACCEPTED
            ),

            joined_at=(

                current_time

                if is_instant_meeting

                else None
            ),

            is_present=is_instant_meeting,

            can_invite=True,

            can_moderate=True,
        )

    # =====================================================
    # ADD PARTICIPANTS
    # =====================================================

    @staticmethod
    def add_participants(
        *,
        meeting,
        membership_ids,
        invited_by,
    ):

        membership_ids = set(
            membership_ids
        )

        membership_ids.discard(
            invited_by.id
        )

        valid_memberships = (

            Membership.objects

            .filter(
                id__in=membership_ids,
                company=meeting.company,
                is_active=True,
            )
        )

        valid_membership_ids = set(

            valid_memberships.values_list(
                "id",
                flat=True,
            )
        )

        # =================================================
        # VALIDATION
        # =================================================

        invalid_ids = (
            membership_ids
            - valid_membership_ids
        )

        if invalid_ids:

            raise ValidationError(
                {
                    "membership_ids": (
                        "Some participants are invalid."
                    )
                }
            )

        # =================================================
        # EXISTING PARTICIPANTS
        # =================================================

        existing_participant_ids = set(

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
                membership_id__in=valid_membership_ids,
            )

            .values_list(
                "membership_id",
                flat=True,
            )
        )

        # =================================================
        # FILTER NEW IDS
        # =================================================

        new_memberships = [

            membership

            for membership

            in valid_memberships

            if (
                membership.id
                not in
                existing_participant_ids
            )
        ]

        # =================================================
        # LIMIT VALIDATION
        # =================================================

        existing_count = (

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
            )

            .count()
        )

        total_count = (
            existing_count
            +
            len(new_memberships)
        )

        if (
            total_count
            >
            meeting.max_participants
        ):

            raise ValidationError(
                {
                    "max_participants": (
                        "Participant limit exceeded."
                    )
                }
            )

        # =================================================
        # CREATE OBJECTS
        # =================================================

        participant_objects = [

            MeetingParticipant(

                meeting=meeting,

                membership=membership,

                invited_by=invited_by,

                role=(
                    MeetingParticipant
                    .Role
                    .PARTICIPANT
                ),

                status=(
                    MeetingParticipant
                    .Status
                    .INVITED
                ),
            )

            for membership in new_memberships
        ]

        MeetingParticipant.objects.bulk_create(
            participant_objects,
        )

        return participant_objects


    # =====================================================
    # SYNC PARTICIPANTS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def sync_participants(
        *,
        meeting,
        membership_ids,
        updated_by,
    ):

        membership_ids = set(
            membership_ids
        )

        # =================================================
        # NEVER REMOVE HOST
        # =================================================

        host_ids = set(

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
                role=MeetingParticipant.Role.HOST,
            )

            .values_list(
                "membership_id",
                flat=True,
            )
        )

        membership_ids.update(host_ids)

        # =================================================
        # CURRENT PARTICIPANTS
        # =================================================

        current_participants = (

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
            )
        )

        current_ids = set(

            current_participants.values_list(
                "membership_id",
                flat=True,
            )
        )

        # =================================================
        # DETERMINE CHANGES
        # =================================================

        ids_to_add = (
            membership_ids
            - current_ids
        )

        ids_to_remove = (
            current_ids
            - membership_ids
        )

        # =================================================
        # REMOVE PARTICIPANTS
        # =================================================

        if ids_to_remove:

            MeetingParticipant.objects.filter(

                meeting=meeting,

                membership_id__in=ids_to_remove,

            ).exclude(

                role=MeetingParticipant.Role.HOST

            ).delete()

        # =================================================
        # ADD PARTICIPANTS
        # =================================================

        if ids_to_add:

            MeetingParticipantService.add_participants(

                meeting=meeting,

                membership_ids=list(
                    ids_to_add
                ),

                invited_by=updated_by,
            )

        return True

    

    # =====================================================
    # UPDATE ROLE
    # =====================================================

    @staticmethod
    def update_participant_role(
        *,
        actor,
        participant,
        role,
    ):

        meeting = participant.meeting

        # =================================================
        # ACTOR PARTICIPANT
        # =================================================

        actor_participant = (

            MeetingParticipantSelector
            .get_participant(
                meeting=meeting,
                membership=actor,
            )
        )

        if not actor_participant:

            raise ValidationError(
                "Invalid meeting manager."
            )

        # =================================================
        # ONLY HOST CAN MODIFY HOST
        # =================================================

        if (

            participant.role
            ==
            MeetingParticipant.Role.HOST

            and

            actor_participant.role
            !=
            MeetingParticipant.Role.HOST
        ):

            raise ValidationError(
                {
                    "role": (
                        "Only hosts can manage hosts."
                    )
                }
            )

        # =================================================
        # PREVENT REMOVING LAST HOST
        # =================================================

        is_host_removal = (

            participant.role
            ==
            MeetingParticipant.Role.HOST

            and

            role
            !=
            MeetingParticipant.Role.HOST
        )

        if is_host_removal:

            host_count = (

                MeetingParticipantSelector
                .get_hosts(
                    meeting=meeting,
                )
                .count()
            )

            if host_count <= 1:

                raise ValidationError(
                    {
                        "role": (
                            "Meeting must have "
                            "at least one host."
                        )
                    }
                )

        # =================================================
        # UPDATE ROLE
        # =================================================

        participant.role = role

        participant.save(
            update_fields=[
                "role",
                "updated_at",
            ]
        )

        return participant

    # =====================================================
    # REMOVE PARTICIPANT
    # =====================================================

    @staticmethod
    def remove_participant(
        *,
        participant,
    ):

        if (
            participant.role
            ==
            MeetingParticipant.Role.HOST
        ):

            raise ValidationError(
                {
                    "participant": (
                        "Host cannot be removed."
                    )
                }
            )

        participant.delete()

    # =====================================================
    # MARK JOINED
    # =====================================================

    @staticmethod
    def mark_joined(
        *,
        participant,
        joined_at,
    ):

        participant.status = (
            MeetingParticipant.Status.JOINED
        )

        participant.is_present = True

        participant.joined_count += 1

        participant.joined_at = joined_at

        participant.save(
            update_fields=[
                "status",
                "is_present",
                "joined_count",
                "joined_at",
                "updated_at",
            ]
        )

        return participant

    # =====================================================
    # MARK LEFT
    # =====================================================

    @staticmethod
    def mark_left(
        *,
        participant,
        left_at,
    ):

        participant.status = (
            MeetingParticipant.Status.LEFT
        )

        participant.is_present = False

        participant.left_at = left_at

        participant.save(
            update_fields=[
                "status",
                "is_present",
                "left_at",
                "updated_at",
            ]
        )

        return participant