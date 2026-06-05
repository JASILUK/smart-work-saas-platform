from apps.meetings.selectors.participant_selectors import MeetingParticipantSelector
from apps.meetings.services.recurrence_service import MeetingRecurrenceService
from apps.meetings.validators.recurrence_validator import RecurrenceValidator
from apps.reminders.validators.reminder_validator import ReminderValidator
from django.utils import timezone
from rest_framework import serializers

from apps.companies.models import (
    Department,
)

from apps.meetings.models.meeting import (
    Meeting,
    MeetingTarget,
)
from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.models.participant import (
    MeetingParticipant,
)


# =========================================================
# TARGET INPUT
# =========================================================

class MeetingTargetInputSerializer(
    serializers.Serializer
):

    target_type = serializers.ChoiceField(
        choices=MeetingTarget.TargetType.choices,
    )

    target_id = serializers.IntegerField(
        min_value=1,
    )


# =========================================================
# TARGET OUTPUT
# =========================================================

class MeetingTargetOutputSerializer(
    serializers.ModelSerializer
):

    target_name = serializers.SerializerMethodField()

    class Meta:

        model = MeetingTarget

        fields = [
            "id",
            "target_type",
            "target_id",
            "target_name",
        ]

    # =====================================================
    # TARGET NAME
    # =====================================================

    def get_target_name(
        self,
        obj,
    ):

        target_map = self.context.get(
            "target_map",
            {},
        )

        return target_map.get(
            (
                obj.target_type,
                obj.target_id,
            )
        )


# =========================================================
# PARTICIPANT SUMMARY
# =========================================================

class MeetingParticipantSummarySerializer(
    serializers.ModelSerializer
):

    membership_id = serializers.IntegerField(
        source="membership.id",
    )

    username = serializers.CharField(
        source="membership.user.username",
    )

    class Meta:

        model = MeetingParticipant

        fields = [

            # =============================================
            # BASIC
            # =============================================

            "id",
            "membership_id",
            "username",

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
        ]
# =========================================================
# CREATE SERIALIZER
# =========================================================

class MeetingCreateSerializer(
    serializers.Serializer
):

    # =====================================================
    # BASIC
    # =====================================================

    title = serializers.CharField(
        max_length=255,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    agenda = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    # =====================================================
    # CONFIG
    # =====================================================

    category = serializers.ChoiceField(
        choices=Meeting.Category.choices,
    )

    visibility = serializers.ChoiceField(
        choices=Meeting.Visibility.choices,
    )

    schedule_type = serializers.ChoiceField(
        choices=Meeting.ScheduleType.choices,
    )

    # =====================================================
    # TIME
    # =====================================================

    scheduled_start = serializers.DateTimeField()

    scheduled_end = serializers.DateTimeField()

    timezone = serializers.CharField(
        default="UTC",
    )

    recurrence_rule = serializers.JSONField(
        required=False,
        allow_null=True,
    )


    reminder_minutes = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )

    # =====================================================
    # TARGETING
    # =====================================================

    targets = MeetingTargetInputSerializer(
        many=True,
        required=False,
        default=list,
    )

    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        default=list,
    )

    # =====================================================
    # OPTIONS
    # =====================================================

    max_participants = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
    )

    waiting_room_enabled = serializers.BooleanField(
        required=False,
        default=False,
    )

    recording_enabled = serializers.BooleanField(
        required=False,
        default=False,
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(
        self,
        attrs,
    ):

        scheduled_start = attrs.get(
            "scheduled_start"
        )

        scheduled_end = attrs.get(
            "scheduled_end"
        )

        visibility = attrs.get(
            "visibility"
        )

        schedule_type = attrs.get(
            "schedule_type"
        )

        recurrence_rule = attrs.get(
            "recurrence_rule"
        )

        targets = attrs.get(
            "targets",
            [],
        )

        participant_ids = attrs.get(
            "participant_ids",
            [],
        )

        # =================================================
        # TIME
        # =================================================

        if scheduled_end <= scheduled_start:

            raise serializers.ValidationError(
                {
                    "scheduled_end": (
                        "Meeting end time must "
                        "be after start time."
                    )
                }
            )
        

        if (
            schedule_type != Meeting.ScheduleType.INSTANT
            and scheduled_start <= timezone.now()
        ):
            raise serializers.ValidationError(
                {
                    "scheduled_start": (
                        "Meeting must be scheduled in the future."
                    )
                }
            )   

        # =================================================
        # RECURRING
        # =================================================

        if (
            schedule_type
            ==
            Meeting.ScheduleType.RECURRING
        ):

            RecurrenceValidator.validate(
                recurrence_rule
            )

        
        # =================================================
        # REMINDERS
        # =================================================

        reminder_minutes = attrs.get(
            "reminder_minutes",
            [],
        )

        if len(reminder_minutes) != len(set(reminder_minutes)):

            raise serializers.ValidationError(
                {
                    "reminder_minutes": (
                        "Duplicate reminder values "
                        "are not allowed."
                    )
                }
            )

        for minutes in reminder_minutes:

            if (
                minutes
                not in
                ReminderValidator.ALLOWED_MINUTES
            ):

                raise serializers.ValidationError(
                    {
                        "reminder_minutes": (
                            "Invalid reminder value."
                        )
                    }
                )
            
        # =================================================
        # TARGETED
        # =================================================

        if (
            visibility
            ==
            Meeting.Visibility.TARGETED
            and
            not targets
        ):

            raise serializers.ValidationError(
                {
                    "targets": (
                        "Targeted meetings require "
                        "at least one target."
                    )
                }
            )

        # =================================================
        # PRIVATE
        # =================================================

        if (
            visibility
            ==
            Meeting.Visibility.PRIVATE
            and
            not participant_ids
        ):

            raise serializers.ValidationError(
                {
                    "participant_ids": (
                        "Private meetings require "
                        "participants."
                    )
                }
            )

        return attrs


# =========================================================
# UPDATE SERIALIZER
# =========================================================

class MeetingUpdateSerializer(
    serializers.Serializer
):

    title = serializers.CharField(
        max_length=255,
        required=False,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    agenda = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    category = serializers.ChoiceField(
        choices=Meeting.Category.choices,
        required=False,
    )

    visibility = serializers.ChoiceField(
        choices=Meeting.Visibility.choices,
        required=False,
    )

    scheduled_start = serializers.DateTimeField(
        required=False,
    )

    scheduled_end = serializers.DateTimeField(
        required=False,
    )

    timezone = serializers.CharField(
        required=False,
    )

    recurrence_rule = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    reminder_minutes = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    targets = MeetingTargetInputSerializer(
        many=True,
        required=False,
    )

    max_participants = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    waiting_room_enabled = serializers.BooleanField(
        required=False,
    )

    recording_enabled = serializers.BooleanField(
        required=False,
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(
        self,
        attrs,
    ):

        instance = self.instance

        scheduled_start = attrs.get(
            "scheduled_start",
            instance.scheduled_start,
        )

        scheduled_end = attrs.get(
            "scheduled_end",
            instance.scheduled_end,
        )

        visibility = attrs.get(
            "visibility",
            instance.visibility,
        )

        schedule_type = instance.schedule_type

        recurrence_rule = attrs.get(
            "recurrence_rule",
            instance.recurrence_rule,
        )

        targets = attrs.get(
            "targets",
            None,
        )


        participant_ids = attrs.get(
            "participant_ids",
            None,
        )

        if (
            visibility
            ==
            Meeting.Visibility.PRIVATE
            and participant_ids is not None
            and not participant_ids
        ):

            raise serializers.ValidationError(
                {
                    "participant_ids": (
                        "Private meetings require "
                        "participants."
                    )
                }
            )

        # =================================================
        # TIME
        # =================================================

        if scheduled_end <= scheduled_start:

            raise serializers.ValidationError(
                {
                    "scheduled_end": (
                        "Meeting end time must "
                        "be after start time."
                    )
                }
            )

        # =================================================
        # RECURRING
        # =================================================

        if (
            schedule_type
            ==
            Meeting.ScheduleType.RECURRING
        ):

            RecurrenceValidator.validate(
                recurrence_rule
            )

        
        # =================================================
        # REMINDERS
        # =================================================

        reminder_minutes = attrs.get(
            "reminder_minutes",
            [],
        )

        if len(reminder_minutes) != len(set(reminder_minutes)):

            raise serializers.ValidationError(
                {
                    "reminder_minutes": (
                        "Duplicate reminder values "
                        "are not allowed."
                    )
                }
            )

        for minutes in reminder_minutes:

            if (
                minutes
                not in
                ReminderValidator.ALLOWED_MINUTES
            ):

                raise serializers.ValidationError(
                    {
                        "reminder_minutes": (
                            "Invalid reminder value."
                        )
                    }
                )

        # =================================================
        # TARGETED
        # =================================================

        if (
            visibility
            ==
            Meeting.Visibility.TARGETED
        ):

            final_targets = (

                targets

                if targets is not None

                else instance.targets.all()
            )

            if not final_targets:

                raise serializers.ValidationError(
                    {
                        "targets": (
                            "Targeted meetings require "
                            "at least one target."
                        )
                    }
                )

        return attrs

# =========================================================
# LIST SERIALIZER
# =========================================================

class MeetingListSerializer(
    serializers.ModelSerializer
):

    created_by = serializers.CharField(
        source=(
            "created_by_membership.user.username"
        )
    )

    participant_count = serializers.SerializerMethodField()

    target_count = serializers.SerializerMethodField()
    
    next_occurrence = serializers.SerializerMethodField()

    class Meta:

        model = Meeting

        fields = [
            "public_id",
            "title",
            "category",
            "visibility",

            "schedule_type",
            "recurrence_rule",

            "status",

            "scheduled_start",
            "scheduled_end",

            "next_occurrence",

            "timezone",

            "created_by",

            "participant_count",
            "target_count",
        ]

    def get_participant_count(
        self,
        obj,
    ):

        return obj.participants.count()

    def get_target_count(
        self,
        obj,
    ):

        return obj.targets.count()
    
    def get_next_occurrence(
        self,
        obj,
    ):

        return (
            MeetingRecurrenceService
            .get_next_occurrence(
                meeting=obj,
            )
        )


# =========================================================
# DETAIL SERIALIZER
# =========================================================

class MeetingDetailSerializer(
    serializers.ModelSerializer
):

    created_by = serializers.CharField(
        source=(
            "created_by_membership.user.username"
        )
    )

    participants = (
        MeetingParticipantSummarySerializer(
            many=True,
            read_only=True,
        )
    )

    targets = serializers.SerializerMethodField()

    current_membership_id = serializers.SerializerMethodField()

    # =====================================================
    # CAPABILITIES
    # =====================================================

    can_manage = serializers.SerializerMethodField()

    can_edit = serializers.SerializerMethodField()

    can_cancel = serializers.SerializerMethodField()

    can_join = serializers.SerializerMethodField()

    can_start_session = serializers.SerializerMethodField()

    can_end_session = serializers.SerializerMethodField()

    next_occurrence = serializers.SerializerMethodField()

    class Meta:

        model = Meeting

        fields = [
            "public_id",
            "title",
            "description",
            "agenda",
            "category",
            "visibility",
            "schedule_type",
            "recurrence_rule",
            "reminder_minutes",
            "status",
            "scheduled_start",
            "scheduled_end",
            "next_occurrence",
            "timezone",
            "max_participants",
            "waiting_room_enabled",
            "recording_enabled",
            "created_by",
            "participants",
            "targets",
            "current_membership_id",

            # capabilities
            "can_manage",
            "can_edit",
            "can_cancel",
            "can_join",
            "can_start_session",
            "can_end_session",

            "created_at",
            "started_at",
            "ended_at",
        ]

    # =====================================================
    # TARGETS
    # =====================================================

    def get_targets(
        self,
        obj,
    ):

        serializer = (

            MeetingTargetOutputSerializer(

                obj.targets.all(),

                many=True,

                context=self.context,
            )
        )

        return serializer.data
    

    def get_current_membership_id(
        self,
        obj,
    ):

        membership = self.get_membership()

        if not membership:
            return None

        return membership.id
    
    def get_next_occurrence(
        self,
        obj,
    ):

        return (
            MeetingRecurrenceService
            .get_next_occurrence(
                meeting=obj,
            )
        )

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def get_membership(
        self,
    ):

        request = self.context.get(
            "request"
        )

        if not request:
            return None

        return getattr(
            request,
            "membership",
            None,
        )

    def is_live(
        self,
        obj,
    ):

        return (
            obj.status
            ==
            Meeting.Status.LIVE
        )

    def is_completed(
        self,
        obj,
    ):

        return obj.status in [
            Meeting.Status.COMPLETED,
            Meeting.Status.CANCELLED,
        ]

    # =====================================================
    # CAN MANAGE
    # =====================================================

    def get_can_manage(
        self,
        obj,
    ):

        membership = self.get_membership()

        if not membership:
            return False

        return (
            MeetingParticipantSelector
            .can_manage_meeting(
                meeting=obj,
                membership=membership,
            )
        )
    # =====================================================
    # CAN EDIT
    # =====================================================

    def get_can_edit(
        self,
        obj,
    ):

        if self.is_completed(obj):
            return False

        return self.get_can_manage(obj)

    # =====================================================
    # CAN CANCEL
    # =====================================================

    def get_can_cancel(
        self,
        obj,
    ):

        if self.is_completed(obj):
            return False

        return self.get_can_manage(obj)

    # =====================================================
    # CAN JOIN
    # =====================================================

    def get_can_join(
        self,
        obj,
    ):

        membership = self.get_membership()

        if not membership:
            return False

        is_participant = (

            obj.participants.filter(
                membership_id=membership.id,
            )

            .exists()
        )

        if not is_participant:
            return False

        return (
            obj.status
            ==
            Meeting.Status.LIVE
        )
    # =====================================================
    # CAN START SESSION
    # =====================================================

    def get_can_start_session(
        self,
        obj,
    ):

        if self.is_completed(obj):
            return False

        if obj.status != Meeting.Status.SCHEDULED:
            return False

        return self.get_can_manage(obj)

    # =====================================================
    # CAN END SESSION
    # =====================================================

    def get_can_end_session(
        self,
        obj,
    ):

        if obj.status != Meeting.Status.LIVE:
            return False

        return self.get_can_manage(obj)