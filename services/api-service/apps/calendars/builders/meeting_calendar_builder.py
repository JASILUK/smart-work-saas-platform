from django.utils.html import strip_tags
from zoneinfo import ZoneInfo


class MeetingCalendarBuilder:

    @classmethod
    def build(
        cls,
        *,
        content_object,
    ):

        tz = ZoneInfo(
            content_object.timezone
        )

        start_local = (
            content_object
            .scheduled_start
            .astimezone(tz)
        )

        end_local = (
            content_object
            .scheduled_end
            .astimezone(tz)
        )

        return {

            "summary": cls.build_title(
                meeting=content_object,
            ),

            "description": cls.build_description(
                meeting=content_object,
            ),

            "start": {
                "dateTime": (
                    start_local
                    .replace(tzinfo=None)
                    .isoformat()
                ),
                "timeZone":
                    content_object.timezone,
            },

            "end": {
                "dateTime": (
                    end_local
                    .replace(tzinfo=None)
                    .isoformat()
                ),
                "timeZone":
                    content_object.timezone,
            },
        }

    # =====================================================
    # TITLE
    # =====================================================

    @staticmethod
    def build_title(
        *,
        meeting,
    ):

        return (
            meeting.title
            or
            "Meeting"
        )

    # =====================================================
    # DESCRIPTION
    # =====================================================

    @staticmethod
    def build_description(
        *,
        meeting,
    ):

        description_parts = []

        if getattr(
            meeting,
            "description",
            None,
        ):

            description_parts.append(

                strip_tags(
                    meeting.description
                )
            )

        if getattr(
            meeting,
            "meeting_type",
            None,
        ):

            description_parts.append(

                (
                    f"Type: "
                    f"{meeting.meeting_type}"
                )
            )

        if getattr(
            meeting,
            "location",
            None,
        ):

            description_parts.append(

                (
                    f"Location: "
                    f"{meeting.location}"
                )
            )

        return "\n\n".join(
            description_parts
        )