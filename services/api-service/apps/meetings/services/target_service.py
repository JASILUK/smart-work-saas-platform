from django.core.exceptions import ValidationError
from django.db import transaction

from apps.companies.models import (
    Department,
)

from apps.meetings.models.meeting import (
    Meeting,
    MeetingTarget,
)

# FUTURE
# from apps.projects.models import Project
# from apps.teams.models import Team


class MeetingTargetService:

    # =====================================================
    # VALIDATE TARGETS
    # =====================================================

    @staticmethod
    def validate_targets(
        *,
        company,
        targets,
    ):

        if not targets:

            raise ValidationError(
                {
                    "targets": (
                        "At least one target "
                        "is required."
                    )
                }
            )

        validated_targets = []

        seen_targets = set()

        for target in targets:

            target_type = target.get(
                "target_type"
            )

            target_id = target.get(
                "target_id"
            )

            # =================================================
            # REQUIRED
            # =================================================

            if not target_type:

                raise ValidationError(
                    {
                        "target_type": (
                            "Target type is required."
                        )
                    }
                )

            if not target_id:

                raise ValidationError(
                    {
                        "target_id": (
                            "Target id is required."
                        )
                    }
                )

            # =================================================
            # DUPLICATE CHECK
            # =================================================

            target_key = (
                target_type,
                target_id,
            )

            if target_key in seen_targets:

                raise ValidationError(
                    {
                        "targets": (
                            "Duplicate targets "
                            "are not allowed."
                        )
                    }
                )

            seen_targets.add(
                target_key
            )

            # =================================================
            # DEPARTMENT
            # =================================================

            if (
                target_type
                ==
                MeetingTarget.TargetType.DEPARTMENT
            ):

                exists = (

                    Department.objects

                    .filter(
                        id=target_id,
                        company=company,
                    )

                    .exists()
                )

                if not exists:

                    raise ValidationError(
                        {
                            "targets": (
                                f"Department "
                                f"{target_id} "
                                f"does not exist."
                            )
                        }
                    )

            # =================================================
            # PROJECT
            # =================================================

            elif (
                target_type
                ==
                MeetingTarget.TargetType.PROJECT
            ):

                # FUTURE PROJECT VALIDATION
                pass

            # =================================================
            # TEAM
            # =================================================

            elif (
                target_type
                ==
                MeetingTarget.TargetType.TEAM
            ):

                # FUTURE TEAM VALIDATION
                pass

            # =================================================
            # INVALID TYPE
            # =================================================

            else:

                raise ValidationError(
                    {
                        "target_type": (
                            "Invalid target type."
                        )
                    }
                )

            validated_targets.append(
                {
                    "target_type": target_type,
                    "target_id": target_id,
                }
            )

        return validated_targets

    # =====================================================
    # CREATE TARGET OBJECTS
    # =====================================================

    @staticmethod
    def build_target_objects(
        *,
        meeting,
        created_by_membership,
        validated_targets,
    ):

        target_objects = []

        for target in validated_targets:

            target_objects.append(

                MeetingTarget(

                    meeting=meeting,

                    target_type=target.get(
                        "target_type"
                    ),

                    target_id=target.get(
                        "target_id"
                    ),

                    created_by_membership=(
                        created_by_membership
                    ),
                )
            )

        return target_objects

    # =====================================================
    # ATTACH TARGETS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def attach_targets(
        *,
        meeting,
        company,
        created_by_membership,
        targets,
    ):

        validated_targets = (

            MeetingTargetService
            .validate_targets(

                company=company,

                targets=targets,
            )
        )

        target_objects = (

            MeetingTargetService
            .build_target_objects(

                meeting=meeting,

                created_by_membership=(
                    created_by_membership
                ),

                validated_targets=(
                    validated_targets
                ),
            )
        )

        MeetingTarget.objects.bulk_create(
            target_objects,
        )

        return target_objects

    # =====================================================
    # REPLACE TARGETS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def replace_targets(
        *,
        meeting,
        company,
        updated_by_membership,
        targets,
    ):

        validated_targets = (

            MeetingTargetService
            .validate_targets(

                company=company,

                targets=targets,
            )
        )

        # =================================================
        # DELETE OLD
        # =================================================

        meeting.targets.all().delete()

        # =================================================
        # CREATE NEW
        # =================================================

        target_objects = (

            MeetingTargetService
            .build_target_objects(

                meeting=meeting,

                created_by_membership=(
                    updated_by_membership
                ),

                validated_targets=(
                    validated_targets
                ),
            )
        )

        MeetingTarget.objects.bulk_create(
            target_objects,
        )

        return target_objects

    # =====================================================
    # CLEAR TARGETS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def clear_targets(
        *,
        meeting,
    ):

        if (
            meeting.visibility
            ==
            Meeting.Visibility.TARGETED
        ):

            raise ValidationError(
                {
                    "targets": (
                        "Targeted meetings "
                        "must have targets."
                    )
                }
            )

        meeting.targets.all().delete()


    @staticmethod
    @transaction.atomic
    def add_target(
        *,
        meeting,
        company,
        created_by_membership,
        target_data,
    ):

        existing = (

            MeetingTarget.objects

            .filter(
                meeting=meeting,
                target_type=target_data.get(
                    "target_type"
                ),
                target_id=target_data.get(
                    "target_id"
                ),
            )

            .exists()
        )

        if existing:

            raise ValidationError(
                {
                    "target": (
                        "Target already exists."
                    )
                }
            )

        validated_targets = (

            MeetingTargetService
            .validate_targets(
                company=company,
                targets=[target_data],
            )
        )

        target = validated_targets[0]

        return MeetingTarget.objects.create(

            meeting=meeting,

            target_type=target.get(
                "target_type"
            ),

            target_id=target.get(
                "target_id"
            ),

            created_by_membership=(
                created_by_membership
            ),
        )

    # =====================================================
    # UPDATE TARGET
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_target(
        *,
        company,
        target,
        validated_data,
    ):

        validated_targets = (

            MeetingTargetService
            .validate_targets(
                company=company,
                targets=[validated_data],
            )
        )

        validated_target = validated_targets[0]

        duplicate_exists = (

            MeetingTarget.objects

            .filter(
                meeting=target.meeting,

                target_type=(
                    validated_target.get(
                        "target_type"
                    )
                ),

                target_id=(
                    validated_target.get(
                        "target_id"
                    )
                ),
            )

            .exclude(
                id=target.id,
            )

            .exists()
        )

        if duplicate_exists:

            raise ValidationError(
                {
                    "target": (
                        "Duplicate target exists."
                    )
                }
            )

        target.target_type = (
            validated_target.get(
                "target_type"
            )
        )

        target.target_id = (
            validated_target.get(
                "target_id"
            )
        )

        target.save(
            update_fields=[
                "target_type",
                "target_id",
                "updated_at",
            ]
        )

        return target

    # =====================================================
    # DELETE TARGET
    # =====================================================

    @staticmethod
    @transaction.atomic
    def delete_target(
        *,
        target,
    ):

        meeting = target.meeting

        if (
            meeting.visibility
            ==
            Meeting.Visibility.TARGETED
        ):

            remaining_targets = (

                meeting.targets

                .exclude(id=target.id)

                .count()
            )

            if remaining_targets <= 0:

                raise ValidationError(
                    {
                        "targets": (
                            "Targeted meetings "
                            "must contain at least "
                            "one target."
                        )
                    }
                )

        target.delete()