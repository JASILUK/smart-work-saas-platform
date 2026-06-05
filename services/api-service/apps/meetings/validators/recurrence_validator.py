from django.utils.dateparse import (
    parse_datetime,
)

from rest_framework import serializers


class RecurrenceValidator:

    ALLOWED_FREQUENCIES = [
        "daily",
        "weekly",
        "monthly",
    ]

    ALLOWED_WEEK_DAYS = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    @classmethod
    def validate(
        cls,
        recurrence_rule,
    ):

        if not recurrence_rule:

            raise serializers.ValidationError(
                "Recurrence rule is required."
            )

        if not isinstance(
            recurrence_rule,
            dict,
        ):

            raise serializers.ValidationError(
                "Recurrence rule must be an object."
            )

        frequency = recurrence_rule.get(
            "frequency"
        )

        interval = recurrence_rule.get(
            "interval",
            1,
        )

        # ==========================================
        # FREQUENCY
        # ==========================================

        if frequency not in cls.ALLOWED_FREQUENCIES:

            raise serializers.ValidationError(
                {
                    "frequency":
                    (
                        "Invalid frequency."
                    )
                }
            )

        # ==========================================
        # INTERVAL
        # ==========================================

        if not isinstance(
            interval,
            int,
        ):

            raise serializers.ValidationError(
                {
                    "interval":
                    (
                        "Interval must be an integer."
                    )
                }
            )

        if interval < 1:

            raise serializers.ValidationError(
                {
                    "interval":
                    (
                        "Interval must be greater than zero."
                    )
                }
            )

        # ==========================================
        # UNTIL
        # ==========================================

        until = recurrence_rule.get(
            "until"
        )

        if until is not None:

            if not isinstance(
                until,
                str,
            ):

                raise serializers.ValidationError(
                    {
                        "until":
                        (
                            "until must be an ISO datetime string or null."
                        )
                    }
                )

            if parse_datetime(until) is None:

                raise serializers.ValidationError(
                    {
                        "until":
                        (
                            "Invalid datetime format."
                        )
                    }
                )

        # ==========================================
        # DAILY
        # ==========================================

        if frequency == "daily":

            if "days" in recurrence_rule:

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "days is not allowed for daily recurrence."
                        )
                    }
                )

            if "day_of_month" in recurrence_rule:

                raise serializers.ValidationError(
                    {
                        "day_of_month":
                        (
                            "day_of_month is not allowed for daily recurrence."
                        )
                    }
                )

            return recurrence_rule

        # ==========================================
        # WEEKLY
        # ==========================================

        if frequency == "weekly":

            if "day_of_month" in recurrence_rule:

                raise serializers.ValidationError(
                    {
                        "day_of_month":
                        (
                            "day_of_month is not allowed for weekly recurrence."
                        )
                    }
                )

            days = recurrence_rule.get(
                "days"
            )

            if not days:

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "Weekly recurrence requires at least one day."
                        )
                    }
                )

            if not isinstance(
                days,
                list,
            ):

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "Days must be a list."
                        )
                    }
                )

            invalid_days = [

                day

                for day in days

                if day not in cls.ALLOWED_WEEK_DAYS
            ]

            if invalid_days:

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "Invalid weekday values."
                        )
                    }
                )

            if len(days) != len(set(days)):

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "Duplicate weekdays are not allowed."
                        )
                    }
                )

            return recurrence_rule

        # ==========================================
        # MONTHLY
        # ==========================================

        if frequency == "monthly":

            if "days" in recurrence_rule:

                raise serializers.ValidationError(
                    {
                        "days":
                        (
                            "days is not allowed for monthly recurrence."
                        )
                    }
                )

            day_of_month = (
                recurrence_rule.get(
                    "day_of_month"
                )
            )

            if day_of_month is None:

                raise serializers.ValidationError(
                    {
                        "day_of_month":
                        (
                            "Monthly recurrence requires day_of_month."
                        )
                    }
                )

            if not isinstance(
                day_of_month,
                int,
            ):

                raise serializers.ValidationError(
                    {
                        "day_of_month":
                        (
                            "day_of_month must be an integer."
                        )
                    }
                )

            if (
                day_of_month < 1
                or
                day_of_month > 31
            ):

                raise serializers.ValidationError(
                    {
                        "day_of_month":
                        (
                            "day_of_month must be between 1 and 31."
                        )
                    }
                )

            return recurrence_rule

        return recurrence_rule