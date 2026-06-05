from apps.meetings.models.session import (
    MeetingSession,
)


class MeetingSessionSelector:

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def base_queryset():

        return (

            MeetingSession.objects

            .select_related(
                "meeting",
                "meeting__company",
                "started_by",
                "started_by__user",
                "ended_by",
                "ended_by__user",
            )
        )

    # =====================================================
    # GET SESSION
    # =====================================================

    @classmethod
    def get_session(
        cls,
        *,
        meeting,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,
            )

            .first()
        )

    # =====================================================
    # GET LIVE SESSION FOR MEETING
    # =====================================================

    @classmethod
    def get_live_session_for_meeting(
        cls,
        *,
        meeting,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting=meeting,

                session_status=(
                    MeetingSession
                    .SessionStatus
                    .LIVE
                ),
            )

            .first()
        )

    # =====================================================
    # GET COMPANY LIVE SESSIONS
    # =====================================================

    @classmethod
    def get_company_live_sessions(
        cls,
        *,
        company,
    ):

        return (

            cls.base_queryset()

            .filter(
                meeting__company=company,

                session_status=(
                    MeetingSession
                    .SessionStatus
                    .LIVE
                ),
            )

            .order_by(
                "-started_at",
            )
        )

    # =====================================================
    # GET WAITING SESSIONS
    # =====================================================

    @classmethod
    def get_waiting_sessions(
        cls,
        *,
        company=None,
    ):

        queryset = (

            cls.base_queryset()

            .filter(
                session_status=(
                    MeetingSession
                    .SessionStatus
                    .WAITING
                ),
            )
        )

        if company:

            queryset = queryset.filter(
                meeting__company=company,
            )

        return queryset.order_by(
            "meeting__scheduled_start",
        )

    # =====================================================
    # GET ENDED SESSIONS
    # =====================================================

    @classmethod
    def get_ended_sessions(
        cls,
        *,
        company=None,
    ):

        queryset = (

            cls.base_queryset()

            .filter(
                session_status=(
                    MeetingSession
                    .SessionStatus
                    .ENDED
                ),
            )
        )

        if company:

            queryset = queryset.filter(
                meeting__company=company,
            )

        return queryset.order_by(
            "-ended_at",
        )