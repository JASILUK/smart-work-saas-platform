from apps.meetings.models.participant import (
    MeetingParticipant,
)


class MeetingParticipantSelector:

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def base_queryset():

        return (

            MeetingParticipant.objects

            .select_related(
                "membership",
                "membership__user",
                "meeting",
            )
        )

    # =====================================================
    # GET BY ID
    # =====================================================

    @classmethod
    def get_by_id(
        cls,
        *,
        meeting,
        participant_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
                id=participant_id,
            )

            .first()
        )

    # =====================================================
    # SINGLE PARTICIPANT
    # =====================================================

    @classmethod
    def get_participant(
        cls,
        *,
        meeting,
        membership,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
                membership=membership,
            )

            .first()
        )

    # =====================================================
    # ALL PARTICIPANTS
    # =====================================================

    @classmethod
    def get_meeting_participants(
        cls,
        *,
        meeting,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
            )

            .order_by("id")
        )

    # =====================================================
    # ACTIVE PARTICIPANTS
    # =====================================================

    @classmethod
    def get_active_participants(
        cls,
        *,
        meeting,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
                is_present=True,
            )
        )

    # =====================================================
    # HOSTS
    # =====================================================

    @classmethod
    def get_hosts(
        cls,
        *,
        meeting,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,

                role__in=[
                    MeetingParticipant.Role.HOST,
                    MeetingParticipant.Role.CO_HOST,
                ],
            )
        )

    # =====================================================
    # CAN MANAGE
    # =====================================================

    @classmethod
    def can_manage_meeting(
        cls,
        *,
        meeting,
        membership,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,

                membership_id=membership.id,

                role__in=[
                    MeetingParticipant.Role.HOST,
                    MeetingParticipant.Role.CO_HOST,
                ],
            )

            .exists()
        )