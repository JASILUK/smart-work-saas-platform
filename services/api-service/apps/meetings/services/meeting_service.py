from django.db import transaction
from django.utils import timezone

from apps.meetings.models.meeting import (
    Meeting,
)

from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.services.meeting_reminder_service import MeetingReminderService
from apps.meetings.services.target_service import (
    MeetingTargetService,
)

from apps.meetings.services.participant_service import (
    MeetingParticipantService,
)


class MeetingService:

    # =====================================================
    # CREATE MEETING
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_meeting(
        *,
        company,
        membership,
        validated_data,
    ):

        # =================================================
        # EXTRACT
        # =================================================

        targets_data = validated_data.pop(
            "targets",
            [],
        )

        participant_ids = validated_data.pop(
            "participant_ids",
            [],
        )

        schedule_type = validated_data.get(
            "schedule_type",
        )

        visibility = validated_data.get(
            "visibility",
        )

        

        current_time = timezone.now()

        is_instant_meeting = (
            schedule_type
            ==
            Meeting.ScheduleType.INSTANT
        )

        # =================================================
        # STATUS
        # =================================================

        meeting_status = (
            Meeting.Status.LIVE
            if is_instant_meeting
            else
            Meeting.Status.SCHEDULED
        )

        # =================================================
        # CREATE MEETING
        # =================================================

        meeting = Meeting.objects.create(

        company=company,

        created_by_membership=membership,

        title=validated_data.get(
            "title"
        ),

        description=validated_data.get(
            "description",
            "",
        ),

        agenda=validated_data.get(
            "agenda",
            "",
        ),

        category=validated_data.get(
            "category"
        ),

        visibility=visibility,

        schedule_type=schedule_type,

        status=meeting_status,

        scheduled_start=validated_data.get(
            "scheduled_start"
        ),

        scheduled_end=validated_data.get(
            "scheduled_end"
        ),

        timezone=validated_data.get(
            "timezone",
            "UTC",
        ),

        recurrence_rule=validated_data.get(
            "recurrence_rule"
        ),

        reminder_minutes=validated_data.get(
            "reminder_minutes",
            [],
        ),

        max_participants=validated_data.get(
            "max_participants",
            100,
        ),

        waiting_room_enabled=validated_data.get(
            "waiting_room_enabled",
            False,
        ),

        recording_enabled=validated_data.get(
            "recording_enabled",
            False,
        ),

        started_at=(
            current_time
            if is_instant_meeting
            else None
        ),
    )

        # =================================================
        # CREATE TARGETS
        # =================================================

        if visibility == Meeting.Visibility.TARGETED:

            MeetingTargetService.attach_targets(

                meeting=meeting,

                company=company,

                created_by_membership=membership,

                targets=targets_data,
            )

        # =================================================
        # CREATE HOST
        # =================================================

        MeetingParticipantService.create_host_participant(

            meeting=meeting,

            membership=membership,

            is_instant_meeting=(
                is_instant_meeting
            ),
        )

        # =================================================
        # CREATE PARTICIPANTS
        # =================================================
        if participant_ids :
            MeetingParticipantService.add_participants(

                meeting=meeting,

                membership_ids=participant_ids,
                invited_by=membership,

            )

        # =================================================
        # CREATE SESSION
        # =================================================

        MeetingSession.objects.create(

            meeting=meeting,

            session_status=(

                MeetingSession
                .SessionStatus
                .LIVE

                if is_instant_meeting

                else

                MeetingSession
                .SessionStatus
                .WAITING
            ),

            started_by=(
                membership
                if is_instant_meeting
                else None
            ),

            started_at=(
                current_time
                if is_instant_meeting
                else None
            ),
        )

        # =================================================
        # CREATE REMINDERS
        # =================================================

        if not is_instant_meeting:

            MeetingReminderService.create_meeting_reminders(

                meeting=meeting,

                reminder_minutes=(
                    meeting.reminder_minutes
                ),
            )

        return meeting

    # =====================================================
    # UPDATE MEETING
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_meeting(
        *,
        meeting,
        validated_data,
        updated_by_membership,
    ):

        # =================================================
        # EXTRACT RELATION FIELDS
        # =================================================

        targets = validated_data.pop(
            "targets",
            None,
        )

        participant_ids = validated_data.pop(
            "participant_ids",
            None,
        )

        visibility = validated_data.get(
            "visibility",
            meeting.visibility,
        )

        # =================================================
        # UPDATE BASIC FIELDS
        # =================================================

        update_fields = []

        for field, value in validated_data.items():

            setattr(
                meeting,
                field,
                value,
            )

            update_fields.append(field)

        # =================================================
        # SAVE MEETING
        # =================================================

        if update_fields:

            update_fields.append(
                "updated_at"
            )

            meeting.save(
                update_fields=update_fields,
            )

        # =================================================
        # TARGET MANAGEMENT
        # =================================================

        if visibility == Meeting.Visibility.TARGETED:

            if targets is not None:

                MeetingTargetService.replace_targets(

                    meeting=meeting,

                    company=meeting.company,

                    updated_by_membership=(
                        updated_by_membership
                    ),

                    targets=targets,
                )

        else:

            # =============================================
            # REMOVE TARGETS IF VISIBILITY CHANGED
            # =============================================

            if meeting.targets.exists():

                MeetingTargetService.clear_targets(
                    meeting=meeting,
                )

        # =================================================
        # PARTICIPANT MANAGEMENT
        # =================================================

        if participant_ids is not None:

            MeetingParticipantService.sync_participants(

                meeting=meeting,

                membership_ids=participant_ids,

                updated_by=updated_by_membership,
            )
        
        # =================================================
        # REGENERATE REMINDERS
        # =================================================

        if any(
            field in validated_data
            for field in [
                "scheduled_start",
                "reminder_minutes",
            ]
        ) or participant_ids is not None:

            MeetingReminderService.regenerate_meeting_reminders(
                meeting=meeting,
                reminder_minutes=(
                    meeting.reminder_minutes
                ),
            )

        return meeting

    # =====================================================
    # CANCEL MEETING
    # =====================================================

    @staticmethod
    @transaction.atomic
    def cancel_meeting(
        *,
        meeting,
        cancelled_by,
        reason="",
    ):

        if (
            meeting.status
            ==
            Meeting.Status.COMPLETED
        ):

            raise ValueError(
                "Completed meetings "
                "cannot be cancelled."
            )

        meeting.status = (
            Meeting.Status.CANCELLED
        )

        meeting.cancelled_at = timezone.now()

        meeting.cancelled_by = cancelled_by

        meeting.cancel_reason = reason

        meeting.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
                "cancel_reason",
                "updated_at",
            ]
        )

        # =================================================
        # CANCEL REMINDERS
        # =================================================

        MeetingReminderService.cancel_meeting_reminders(
            meeting=meeting,
        )

        return meeting