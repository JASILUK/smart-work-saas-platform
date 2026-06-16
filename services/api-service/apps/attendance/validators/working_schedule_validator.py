from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)

from django.core.exceptions import ValidationError

from apps.attendance.constants.weekdays import (
    ISO_WEEKDAY_TO_NAME,
    WEEKDAY_ALIASES,
    WEEKDAY_SET,
    WEEKDAYS,
)


class WorkingScheduleValidator:

    """
    Input normalization and validation for company work schedules.

    Used at the API boundary (serializers). Services receive already-normalized
    values but may call derive_weekend_days for business rules.
    """

    # =====================================================
    # WORKING DAYS
    # =====================================================

    @staticmethod
    def normalize_working_days(
        value,
    ):
        """
        Accept and normalize working_days.

        Supported input formats:
        - List of weekday names (case-insensitive):
          ["monday", "tuesday", "friday"]
        - List of short aliases:
          ["mon", "tue", "fri"]
        - List of ISO-8601 integers (1=Monday … 7=Sunday):
          [1, 2, 3, 4, 5]

        Returns canonical lowercase weekday names in ISO week order.
        """

        if value is None:

            raise ValidationError(
                "Working days cannot be empty."
            )

        if not isinstance(value, list):

            raise ValidationError(
                "Working days must be a list of weekday names."
            )

        if not value:

            raise ValidationError(
                "Working days cannot be empty."
            )

        if len(value) > len(WEEKDAYS):

            raise ValidationError(
                "Working days cannot contain more than 7 entries."
            )

        normalized = []
        seen = set()

        for index, raw_day in enumerate(value):

            day_name = (
                WorkingScheduleValidator
                ._resolve_day_name(
                    raw_day=raw_day,
                    index=index,
                )
            )

            if day_name in seen:

                raise ValidationError(
                    f"Duplicate weekday: {day_name}."
                )

            seen.add(day_name)
            normalized.append(day_name)

        ordered = [
            day
            for day in WEEKDAYS
            if day in seen
        ]

        return ordered

    @staticmethod
    def derive_weekend_days(
        working_days,
    ):
        """
        Compute weekend days as the complement of working days.
        """

        working_set = set(working_days)

        return [
            day
            for day in WEEKDAYS
            if day not in working_set
        ]

    # =====================================================
    # TIMEZONE
    # =====================================================

    @staticmethod
    def normalize_timezone(
        value,
    ):
        """
        Validate IANA timezone identifier (e.g. Asia/Kolkata, America/New_York).
        """

        if value is None:

            raise ValidationError(
                "Timezone cannot be blank."
            )

        timezone = str(value).strip()

        if not timezone:

            raise ValidationError(
                "Timezone cannot be blank."
            )

        try:

            ZoneInfo(timezone)

        except ZoneInfoNotFoundError:

            raise ValidationError(
                f"'{timezone}' is not a valid IANA timezone."
            )

        return timezone

    # =====================================================
    # WORK HOURS
    # =====================================================

    @staticmethod
    def validate_work_hours(
        *,
        work_start_time,
        work_end_time,
    ):

        if (
            work_start_time
            and work_end_time
            and work_end_time <= work_start_time
        ):

            raise ValidationError(
                "Work end time must be after work start time."
            )

    # =====================================================
    # INTERNAL
    # =====================================================

    @staticmethod
    def _resolve_day_name(
        *,
        raw_day,
        index,
    ):

        if isinstance(raw_day, bool):

            raise ValidationError(
                f"Invalid weekday at index {index}: boolean values are not allowed."
            )

        if isinstance(raw_day, int):

            if raw_day not in ISO_WEEKDAY_TO_NAME:

                raise ValidationError(
                    f"Invalid weekday number at index {index}: "
                    f"use ISO-8601 values 1 (Monday) through 7 (Sunday)."
                )

            return ISO_WEEKDAY_TO_NAME[raw_day]

        if not isinstance(raw_day, str):

            raise ValidationError(
                f"Invalid weekday at index {index}: "
                f"expected a string or ISO weekday number."
            )

        key = raw_day.strip().lower()

        if not key:

            raise ValidationError(
                f"Invalid weekday at index {index}: blank value."
            )

        if key.isdigit():

            number = int(key)

            if number not in ISO_WEEKDAY_TO_NAME:

                raise ValidationError(
                    f"Invalid weekday number at index {index}: "
                    f"use ISO-8601 values 1 (Monday) through 7 (Sunday)."
                )

            return ISO_WEEKDAY_TO_NAME[number]

        if key in WEEKDAY_ALIASES:

            return WEEKDAY_ALIASES[key]

        if key in WEEKDAY_SET:

            return key

        allowed = ", ".join(WEEKDAYS)

        raise ValidationError(
            f"Invalid weekday '{raw_day}' at index {index}. "
            f"Allowed values: {allowed}."
        )
