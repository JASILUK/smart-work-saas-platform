from calendar import monthrange
from datetime import timedelta
from django.utils import timezone


class MeetingRecurrenceService:

    # =====================================================
    # NEXT OCCURRENCE
    # =====================================================

    @classmethod
    def get_next_occurrence(
        cls,
        *,
        meeting,
        from_date=None,
    ):
        if from_date is None:
            from_date = timezone.now()

        # Ensure from_date is fully offset-aware to match DB timezone rules
        if timezone.is_naive(from_date):
            from_date = timezone.make_aware(from_date, timezone.utc)

        # ==============================================
        # NON RECURRING
        # ==============================================

        if (
            meeting.schedule_type
            != meeting.ScheduleType.RECURRING
        ):
            # Ensure scheduled_start is offset-aware before comparison
            start_time = meeting.scheduled_start
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.utc)

            if start_time >= from_date:
                return start_time

            return None

        recurrence_rule = (
            meeting.recurrence_rule
            or {}
        )

        frequency = recurrence_rule.get(
            "frequency"
        )

        interval = recurrence_rule.get(
            "interval",
            1,
        )

        until = recurrence_rule.get(
            "until"
        )

        current = (
            meeting.scheduled_start
        )
        
        if timezone.is_naive(current):
            current = timezone.make_aware(current, timezone.utc)

        # ==============================================
        # DAILY
        # ==============================================

        if frequency == "daily":
            while current < from_date:
                current += timedelta(
                    days=interval
                )

            return cls.validate_until(
                current=current,
                until=until,
            )

        # ==============================================
        # WEEKLY
        # ==============================================

        if frequency == "weekly":
            days = recurrence_rule.get(
                "days",
                [],
            )

            weekday_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }

            allowed_days = {
                weekday_map[day]
                for day in days
                if day in weekday_map
            }

            # If no allowed days configured, protect against infinite loops
            if not allowed_days:
                return None

            current = from_date

            for _ in range(366):
                if (
                    current.weekday()
                    in allowed_days
                ):
                    occurrence = (
                        current.replace(
                            hour=meeting.scheduled_start.hour,
                            minute=meeting.scheduled_start.minute,
                            second=meeting.scheduled_start.second,
                            microsecond=0,
                        )
                    )

                    if (
                        occurrence
                        >=
                        from_date
                    ):
                        return cls.validate_until(
                            current=occurrence,
                            until=until,
                        )

                current += timedelta(
                    days=1
                )

            return None

        # ==============================================
        # MONTHLY
        # ==============================================

        if frequency == "monthly":
            day_of_month = (
                recurrence_rule.get(
                    "day_of_month"
                )
            )
            
            if not day_of_month:
                return None

            current = from_date

            for _ in range(24):
                last_day = monthrange(
                    current.year,
                    current.month,
                )[1]

                actual_day = min(
                    day_of_month,
                    last_day,
                )

                occurrence = current.replace(
                    day=actual_day,
                    hour=meeting.scheduled_start.hour,
                    minute=meeting.scheduled_start.minute,
                    second=meeting.scheduled_start.second,
                    microsecond=0,
                )

                if (
                    occurrence
                    >=
                    from_date
                ):
                    return cls.validate_until(
                        current=occurrence,
                        until=until,
                    )

                if current.month == 12:
                    current = current.replace(
                        year=current.year + 1,
                        month=1,
                    )
                else:
                    current = current.replace(
                        month=current.month + 1,
                    )

            return None

        return None

    # =====================================================
    # UNTIL
    # =====================================================

    @staticmethod
    def validate_until(
        *,
        current,
        until,
    ):
        if not until:
            return current

        # Convert input string safely to an offset-aware datetime matching UTC format constraints
        until_dt = timezone.datetime.fromisoformat(
            until.replace(
                "Z",
                "+00:00",
                )
            )

        # Force structural normalization matching database layer rules to guarantee clean matching context
        if timezone.is_naive(until_dt):
            until_dt = timezone.make_aware(until_dt, timezone.utc)
            
        if timezone.is_naive(current):
            current = timezone.make_aware(current, timezone.utc)

        if current > until_dt:
            return None

        return current