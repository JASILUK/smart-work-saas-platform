from apps.meetings.models.meeting import (
    Meeting,
)

from apps.calendars.builders.meeting_calendar_builder import (
    MeetingCalendarBuilder,
)


class CalendarEventBuilderFactory:

    BUILDERS = {

        Meeting:
            MeetingCalendarBuilder,

        # Future
        #
        # LeaveRequest:
        #     LeaveCalendarBuilder,
        #
        # Training:
        #     TrainingCalendarBuilder,
    }

    # =====================================================
    # GET BUILDER
    # =====================================================

    @classmethod
    def get_builder(
        cls,
        *,
        content_object,
    ):

        builder_class = (
            cls.BUILDERS.get(
                content_object.__class__
            )
        )

        if not builder_class:

            raise ValueError(
                (
                    "No calendar builder "
                    f"registered for "
                    f"{content_object.__class__.__name__}"
                )
            )

        return builder_class()

    # =====================================================
    # BUILD EVENT PAYLOAD
    # =====================================================

    @classmethod
    def build_payload(
        cls,
        *,
        content_object,
    ):

        builder = cls.get_builder(
            content_object=content_object,
        )

        return builder.build(
            content_object=content_object,
        )