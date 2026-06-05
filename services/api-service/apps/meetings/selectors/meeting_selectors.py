from django.db.models import (
    Prefetch,
    Q,
)

from django.utils import timezone

from apps.meetings.models.meeting import (
    Meeting,MeetingTarget
)

from apps.meetings.models.participant import (
    MeetingParticipant,
)

from apps.meetings.models.session import (
    MeetingSession,
)



class MeetingSelector:

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def base_queryset():

        return (

            Meeting.objects

            .select_related(
                "company",
                "created_by_membership",
                "created_by_membership__user",
            )

            .prefetch_related(

                # =========================================
                # TARGETS
                # =========================================

                "targets",

                # =========================================
                # PARTICIPANTS
                # =========================================

                Prefetch(

                    "participants",

                    queryset=(

                        MeetingParticipant.objects

                        .select_related(
                            "membership",
                            "membership__user",
                        )

                        .only(

                        # =============================================
                        # BASIC
                        # =============================================

                        "id",
                        "meeting_id",
                        "membership_id",

                        # =============================================
                        # ROLE / STATUS
                        # =============================================

                        "role",
                        "status",
                        "attendance_status",

                        # =============================================
                        # PRESENCE
                        # =============================================

                        "is_present",

                        # =============================================
                        # TIME
                        # =============================================

                        "joined_at",
                        "left_at",
                        "last_joined_at",

                        # =============================================
                        # ATTENDANCE
                        # =============================================

                        "attendance_percentage",
                        "attendance_duration_seconds",
                        "joined_count",

                        # =============================================
                        # RELATIONS
                        # =============================================

                        "membership__id",
                        "membership__user__username",
                    )
                    ),
                )
            )
        )

    # =====================================================
    # DETAIL
    # =====================================================

    @classmethod
    def get_by_public_id(
        cls,
        *,
        public_id,
        company,
    ):

        return (

            cls.base_queryset()

            .filter(
                public_id=public_id,
                company=company,
            )

            .first()
        )


    # =====================================================
    # GET BY ID
    # =====================================================

    @classmethod
    def get_by_id(
        cls,
        *,
        meeting_id,
    ):

        return (

            cls.base_queryset()

            .filter(
                id=meeting_id,
            )

            .first()
        )
    
    # =====================================================
    # COMPANY MEETINGS
    # =====================================================

    @classmethod
    def get_company_meetings(
        cls,
        *,
        company,
    ):

        return (

            cls.base_queryset()

            .filter(
                company=company,
            )

            .order_by(
                "-scheduled_start",
            )
        )

    # =====================================================
    # VISIBLE MEETINGS
    # =====================================================

    @classmethod
    def get_visible_meetings_for_membership(
        cls,
        *,
        membership,
        search=None,
        status=None,
        ordering="-scheduled_start",
    ):

        queryset = (

            cls.base_queryset()

            .filter(
                company=membership.company,
            )
        )

        # =================================================
        # BASE VISIBILITY FILTER
        # =================================================

        visibility_filter = (

            # =============================================
            # PUBLIC
            # =============================================

            Q(
                visibility=(
                    Meeting.Visibility.PUBLIC
                ),
            )

            |

            # =============================================
            # ORGANIZATION
            # =============================================

            Q(
                visibility=(
                    Meeting.Visibility.ORGANIZATION
                ),
            )

            |

            # =============================================
            # DIRECT PARTICIPANT
            # =============================================

            Q(
                participants__membership=membership,
            )
        )

        # =================================================
        # TARGETED VISIBILITY
        # =================================================

        if membership.department_id:

            visibility_filter |= (

                Q(
                    visibility=(
                        Meeting.Visibility.TARGETED
                    ),

                    targets__target_type=(
                        MeetingTarget
                        .TargetType
                        .DEPARTMENT
                    ),

                    targets__target_id=(
                        membership.department_id
                    ),
                )
            )

        # =================================================
        # APPLY VISIBILITY
        # =================================================

        queryset = queryset.filter(
            visibility_filter,
        )

        # =================================================
        # SEARCH
        # =================================================

        if search:

            queryset = queryset.filter(

                Q(title__icontains=search)

                |

                Q(description__icontains=search)
            )

        # =================================================
        # STATUS FILTER
        # =================================================

        if status:

            queryset = queryset.filter(
                status=status,
            )

        # =================================================
        # ORDERING
        # =================================================

        allowed_orderings = {
            "scheduled_start",
            "-scheduled_start",
            "created_at",
            "-created_at",
        }

        if ordering not in allowed_orderings:
            ordering = "-scheduled_start"

        return (

            queryset

            .distinct()

            .order_by(ordering)
        )

    # =====================================================
    # UPCOMING
    # =====================================================

    @classmethod
    def get_upcoming_meetings_for_membership(
        cls,
        *,
        membership,
    ):

        return (

            cls.get_visible_meetings_for_membership(
                membership=membership,
            )

            .filter(
                scheduled_start__gte=timezone.now(),
            )

            .exclude(
                status=Meeting.Status.CANCELLED,
            )
        )

    # =====================================================
    # LIVE COMPANY MEETINGS
    # =====================================================

    @classmethod
    def get_live_company_meetings(
        cls,
        *,
        company,
    ):

        return (

            cls.base_queryset()

            .filter(

                company=company,

                session__session_status=(

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
    # TARGET MEETINGS
    # =====================================================

    @classmethod
    def get_target_meetings(
        cls,
        *,
        target_type,
        target_id,
    ):

        return (

            cls.base_queryset()

            .filter(

                targets__target_type=target_type,

                targets__target_id=target_id,
            )

            .distinct()

            .order_by(
                "-scheduled_start",
            )
        )

    # =====================================================
    # PARTICIPANT
    # =====================================================

    @classmethod
    def get_participant(
        cls,
        *,
        meeting,
        membership,
    ):

        return (

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
                membership=membership,
            )

            .first()
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

        participant = cls.get_participant(

            meeting=meeting,

            membership=membership,
        )

        if not participant:
            return False

        return (

            participant.role

            in

            [
                MeetingParticipant.Role.HOST,

                MeetingParticipant.Role.CO_HOST,
            ]
        )
    

    @classmethod
    def can_access_meeting(
        cls,
        *,
        meeting,
        membership,
    ):

        # PUBLIC
        if (
            meeting.visibility
            ==
            Meeting.Visibility.PUBLIC
        ):
            return True

        # ORGANIZATION
        if (
            meeting.visibility
            ==
            Meeting.Visibility.ORGANIZATION
        ):
            return True

        # DIRECT PARTICIPANT
        participant_exists = (

            MeetingParticipant.objects

            .filter(
                meeting=meeting,
                membership=membership,
            )

            .exists()
        )

        if participant_exists:
            return True

        # TARGETED
        if (
            meeting.visibility
            ==
            Meeting.Visibility.TARGETED
        ):

            if membership.department_id:

                has_department_target = (

                    meeting.targets.filter(

                        target_type=(
                            MeetingTarget
                            .TargetType
                            .DEPARTMENT
                        ),

                        target_id=(
                            membership.department_id
                        ),
                    )

                    .exists()
                )

                if has_department_target:
                    return True

        return False