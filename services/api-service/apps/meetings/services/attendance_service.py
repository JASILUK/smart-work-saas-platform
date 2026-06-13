from asgiref.sync import sync_to_async

from django.utils import timezone

from apps.meetings.models.participant import (
    MeetingParticipant,
)

from apps.meetings.selectors.participant_selectors import (
    MeetingParticipantSelector,
)


class MeetingAttendanceService:

    # =====================================================
    # PARTICIPANT JOINED
    # =====================================================

    @classmethod
    async def mark_joined(
        cls,
        *,
        meeting,
        membership,
    ):

        participant = await sync_to_async(
            MeetingParticipantSelector.get_participant
        )(
            meeting=meeting,
            membership=membership,
        )

        if not participant:
            return None

        # Already present → ignore duplicate join

        if participant.is_present:
            return participant

        now = timezone.now()

        # ================================================
        # FIRST JOIN
        # ================================================

        if not participant.joined_at:

            participant.joined_at = now

        # ================================================
        # LAST JOIN
        # ================================================

        participant.last_joined_at = now

        # ================================================
        # STATUS
        # ================================================

        participant.status = (
            MeetingParticipant.Status.JOINED
        )

        participant.attendance_status = (
            "present"
        )

        participant.is_present = True

        # ================================================
        # JOIN COUNT
        # ================================================

        participant.joined_count += 1

        # ================================================
        # SAVE
        # ================================================

        await sync_to_async(
            participant.save
        )(
            update_fields=[

                "joined_at",

                "last_joined_at",

                "status",

                "attendance_status",

                "is_present",

                "joined_count",

                "updated_at",
            ]
        )

        return participant

    # =====================================================
    # PARTICIPANT LEFT
    # =====================================================

    @classmethod
    async def mark_left(
        cls,
        *,
        meeting,
        membership,
    ):

        participant = await sync_to_async(
            MeetingParticipantSelector.get_participant
        )(
            meeting=meeting,
            membership=membership,
        )

        if not participant:
            return None

        # Already left → ignore duplicate leave

        if not participant.is_present:
            return participant
        
        now = timezone.now()

        # ================================================
        # LEFT TIME
        # ================================================

        participant.left_at = now

        # ================================================
        # PRESENCE
        # ================================================

        participant.is_present = False

        participant.status = (
            MeetingParticipant.Status.LEFT
        )

        # ================================================
        # DURATION
        # ================================================

        if participant.last_joined_at:

            session_duration = int(
                (
                    now -
                    participant.last_joined_at
                ).total_seconds()
            )

            if session_duration > 0:

                participant.attendance_duration_seconds += (
                    session_duration
                )

        # ================================================
        # ATTENDANCE %
        # ================================================

        meeting_duration_seconds = int(
            (
                meeting.scheduled_end -
                meeting.scheduled_start
            ).total_seconds()
        )

        if meeting_duration_seconds > 0:

            attendance_percentage = (
                participant.attendance_duration_seconds
                /
                meeting_duration_seconds
            ) * 100

            participant.attendance_percentage = min(
                round(attendance_percentage, 2),
                100,
            )

        # ================================================
        # ATTENDANCE STATUS
        # ================================================

        percentage = (
            participant.attendance_percentage
        )

        if percentage >= 80:

            participant.attendance_status = (
                "full_attendance"
            )

        elif percentage >= 50:

            participant.attendance_status = (
                "present"
            )

        elif percentage > 0:

            participant.attendance_status = (
                "partial"
            )

        else:

            participant.attendance_status = (
                "absent"
            )

        # ================================================
        # SAVE
        # ================================================

        await sync_to_async(
            participant.save
        )(
            update_fields=[

                "left_at",

                "is_present",

                "status",

                "attendance_duration_seconds",

                "attendance_percentage",

                "attendance_status",

                "updated_at",
            ]
        )

        return participant

    # =====================================================
    # MARK NO SHOW
    # =====================================================

    @classmethod
    async def mark_no_show(
        cls,
        *,
        participant,
    ):

        participant.status = (
            MeetingParticipant.Status.NO_SHOW
        )

        participant.attendance_status = (
            "absent"
        )

        participant.is_present = False

        await sync_to_async(
            participant.save
        )(
            update_fields=[

                "status",

                "attendance_status",

                "is_present",

                "updated_at",
            ]
        )

        return participant

    # =====================================================
    # FINALIZE MEETING ATTENDANCE
    # =====================================================

    @classmethod
    async def finalize_meeting_attendance(
        cls,
        *,
        meeting,
    ):

        participants = await sync_to_async(
            list
        )(
            MeetingParticipantSelector
            .get_meeting_participants(
                meeting=meeting,
            )
        )

        for participant in participants:

            # ============================================
            # STILL PRESENT
            # ============================================

            if participant.is_present:

                await cls.mark_left(
                    meeting=meeting,
                    membership=participant.membership,
                )

            # ============================================
            # NEVER JOINED
            # ============================================

            elif (
                participant.joined_count == 0
            ):

                await cls.mark_no_show(
                    participant=participant,
                )