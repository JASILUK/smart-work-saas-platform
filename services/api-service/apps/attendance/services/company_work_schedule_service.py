from django.core.exceptions import ValidationError
from django.db import transaction

from apps.attendance.models.company_work_schedule import (
    CompanyWorkSchedule,
)
from apps.attendance.selectors.company_work_schedule_selector import (
    CompanyWorkScheduleSelector,
)
from apps.attendance.validators.working_schedule_validator import (
    WorkingScheduleValidator,
)


class CompanyWorkScheduleService:

    # =====================================================
    # CREATE SCHEDULE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_schedule(
        *,
        company,
        actor,
        validated_data,
    ):

        if CompanyWorkScheduleSelector.exists_for_company(
            company=company,
        ):
            raise ValidationError(
                "Company work schedule already exists."
            )

        default_shift = validated_data.get(
            "default_shift",
        )

        CompanyWorkScheduleService._validate_default_shift(
            company=company,
            default_shift=default_shift,
        )

        working_days = validated_data[
            "working_days"
        ]

        weekend_days = (
            WorkingScheduleValidator
            .derive_weekend_days(
                working_days,
            )
        )

        schedule = CompanyWorkSchedule.objects.create(

            company=company,

            working_days=working_days,

            weekend_days=weekend_days,

            work_start_time=validated_data[
                "work_start_time"
            ],

            work_end_time=validated_data[
                "work_end_time"
            ],

            break_minutes=validated_data.get(
                "break_minutes",
                60,
            ),

            timezone=validated_data.get(
                "timezone",
            ) or company.timezone ,

            country=validated_data.get(
                "country",
            ) or company.country or "",

            state=validated_data.get(
                "state",
                "",
            ),

            default_shift=default_shift,

            holiday_sync_enabled=validated_data.get(
                "holiday_sync_enabled",
                False,
            ),

            holiday_provider=validated_data.get(
                "holiday_provider",
                "",
            ),

            is_active=validated_data.get(
                "is_active",
                True,
            ),
        )

        return schedule

    # =====================================================
    # UPDATE SCHEDULE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_schedule(
        *,
        schedule,
        actor,
        validated_data,
    ):

        if not validated_data:
            return schedule

        if "default_shift" in validated_data:

            CompanyWorkScheduleService._validate_default_shift(
                company=schedule.company,
                default_shift=validated_data[
                    "default_shift"
                ],
            )

        if "working_days" in validated_data:

            validated_data[
                "weekend_days"
            ] = (
                WorkingScheduleValidator
                .derive_weekend_days(
                    validated_data[
                        "working_days"
                    ],
                )
            )

        update_fields = []

        for field, value in validated_data.items():

            setattr(
                schedule,
                field,
                value,
            )

            update_fields.append(
                field,
            )

        update_fields.append(
            "updated_at",
        )

        schedule.save(
            update_fields=update_fields,
        )

        return schedule

    # =====================================================
    # ACTIVATE SCHEDULE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def activate_schedule(
        *,
        schedule,
        actor,
    ):

        if schedule.is_active:
            return schedule

        schedule.is_active = True

        schedule.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return schedule

    # =====================================================
    # DEACTIVATE SCHEDULE
    # =====================================================

    @staticmethod
    @transaction.atomic
    def deactivate_schedule(
        *,
        schedule,
        actor,
    ):

        if not schedule.is_active:
            return schedule

        schedule.is_active = False

        schedule.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return schedule

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    @staticmethod
    def _validate_default_shift(
        *,
        company,
        default_shift,
    ):

        if default_shift is None:
            return

        if default_shift.company_id != company.id:

            raise ValidationError(
                "Default shift must belong to the company."
            )