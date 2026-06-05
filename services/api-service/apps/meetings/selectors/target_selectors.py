from apps.companies.models import Department
from apps.meetings.models.meeting import (
    MeetingTarget,
)


class MeetingTargetSelector:

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def base_queryset():

        return (

            MeetingTarget.objects

            .select_related(
                "meeting",
                "created_by_membership",
                "created_by_membership__user",
            )
        )

    # =====================================================
    # MEETING TARGETS
    # =====================================================

    @classmethod
    def get_meeting_targets(
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
    # TARGET TYPE
    # =====================================================

    @classmethod
    def get_targets_by_type(
        cls,
        *,
        meeting,
        target_type,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
                target_type=target_type,
            )

            .order_by("id")
        )

    # =====================================================
    # SINGLE TARGET
    # =====================================================

    @classmethod
    def get_target(
        cls,
        *,
        meeting,
        target_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
                id=target_id,
            )

            .first()
        )
    


   

    # =====================================================
    # TARGET MAP
    # =====================================================

    @staticmethod
    def build_target_map(
        *,
        meeting,
    ):

        targets = meeting.targets.all()

        department_ids = [

            target.target_id

            for target in targets

            if (
                target.target_type
                ==
                MeetingTarget.TargetType.DEPARTMENT
            )
        ]

        departments = (

            Department.objects

            .filter(
                id__in=department_ids,
            )

            .only(
                "id",
                "name",
            )
        )

        target_map = {}

        for department in departments:

            target_map[
                (
                    MeetingTarget
                    .TargetType
                    .DEPARTMENT,

                    department.id,
                )
            ] = department.name

        return target_map