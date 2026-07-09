# apps/attendance/api/v1/serializers/hr_live_workforce_serializers.py

import datetime
from rest_framework import serializers
from apps.companies.models import Membership


class LiveWorkforceRowSerializer(serializers.ModelSerializer):
    """
    Serializes a single Live Workforce row.
    Maps annotated database fields to the API contract.
    """

    membership_id = serializers.IntegerField(source="id", read_only=True)
    attendance_record_id = serializers.IntegerField(source="da_record_id", read_only=True)
    
    employee_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    department = serializers.CharField(source="department.name", default="Unassigned")
    job_title = serializers.CharField(source="role.name", default="No Role")
    work_mode = serializers.SerializerMethodField()
    
    shift = serializers.CharField(source="shift_name", default="Unassigned Shift")
    
    # FIXED: Removed redundant source="shift_start" — field name matches annotation
    shift_start = serializers.TimeField(format="%H:%M", read_only=True)
    shift_end = serializers.TimeField(format="%H:%M", read_only=True)
    
    current_status = serializers.CharField(source="computed_status", read_only=True)
    attendance_status = serializers.CharField(source="da_status", default="ABSENT")
    
    first_check_in = serializers.DateTimeField(source="evt_first_in", read_only=True)
    last_event_type = serializers.CharField(source="evt_last_type", read_only=True)
    last_event_time = serializers.DateTimeField(source="evt_last_time", read_only=True)
    last_event_method = serializers.CharField(source="evt_last_method", read_only=True)
    
    working_duration = serializers.SerializerMethodField()
    break_duration = serializers.IntegerField(source="da_break_min", default=0)
    late_minutes = serializers.IntegerField(source="da_late_min", default=0)
    overtime_minutes = serializers.IntegerField(source="da_ot_min", default=0)
    
    needs_review = serializers.BooleanField(source="da_needs_review", default=False)
    review_reason = serializers.CharField(source="da_review_reason", default="")
    auto_closed = serializers.BooleanField(source="da_auto_closed", default=False)
    
    is_late = serializers.SerializerMethodField()
    is_present = serializers.SerializerMethodField()
    
    # FIXED: These annotations match field names exactly, no source needed
    is_on_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            "membership_id",
            "attendance_record_id",
            "employee_name",
            "avatar",
            "department",
            "job_title",
            "work_mode",
            "shift",
            "shift_start",
            "shift_end",
            "current_status",
            "attendance_status",
            "first_check_in",
            "last_event_type",
            "last_event_time",
            "last_event_method",
            "working_duration",
            "break_duration",
            "late_minutes",
            "overtime_minutes",
            "needs_review",
            "review_reason",
            "auto_closed",
            "is_late",
            "is_present",
            "is_on_leave",
            "is_holiday",
            "is_weekend",
        ]

    def get_employee_name(self, obj: Membership) -> str:
        first = getattr(obj.user, "first_name", "") or ""
        last = getattr(obj.user, "last_name", "") or ""
        return f"{first} {last}".strip() or obj.user.username

    def get_avatar(self, obj: Membership) -> str:
        if hasattr(obj, "avatar") and obj.avatar:
            return obj.avatar.url
        first = getattr(obj.user, "first_name", "") or ""
        last = getattr(obj.user, "last_name", "") or ""
        return f"https://ui-avatars.com/api/?name={first}+{last}&background=random"

    def get_work_mode(self, obj: Membership) -> str:
        if getattr(obj, "shift_name", None):
            return "scheduled"
        return "flexible"

    def get_working_duration(self, obj: Membership) -> str:
        """
        Format working duration as human-readable string.
        """
        minutes = getattr(obj, "da_work_min", 0) or 0
        
        if getattr(obj, "computed_status", "") == "WORKING" and minutes == 0:
            first_in = getattr(obj, "evt_first_in", None)
            if first_in:
                now = datetime.datetime.now(datetime.timezone.utc)
                if first_in.tzinfo is None:
                    first_in = first_in.replace(tzinfo=datetime.timezone.utc)
                delta = now - first_in
                minutes = int(delta.total_seconds() // 60)
                break_min = getattr(obj, "da_break_min", 0) or 0
                minutes = max(0, minutes - break_min)

        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def get_is_late(self, obj: Membership) -> bool:
        first_in = getattr(obj, "evt_first_in", None)
        shift_start = getattr(obj, "shift_start", None)
        if first_in and shift_start:
            return first_in.time() > shift_start
        return getattr(obj, "da_late_min", 0) > 0

    def get_is_present(self, obj: Membership) -> bool:
        has_in = getattr(obj, "evt_has_check_in", False)
        has_out = getattr(obj, "evt_has_check_out", False)
        return has_in and not has_out


class FilterMetadataSerializer(serializers.Serializer):
    departments = serializers.ListField(child=serializers.DictField())
    shifts = serializers.ListField(child=serializers.DictField())
    available_statuses = serializers.ListField(child=serializers.DictField())
    current_date = serializers.CharField()


class LiveWorkforceSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    working = serializers.IntegerField()
    break_count = serializers.IntegerField(source="break")
    checked_out = serializers.IntegerField()
    not_started = serializers.IntegerField()
    absent = serializers.IntegerField()
    leave = serializers.IntegerField()
    holiday = serializers.IntegerField()
    weekend = serializers.IntegerField()
    review_required = serializers.IntegerField()


class LiveWorkforceResponseSerializer(serializers.Serializer):
    summary = LiveWorkforceSummarySerializer()
    filter_metadata = FilterMetadataSerializer()
    results = LiveWorkforceRowSerializer(many=True)
    pagination = serializers.DictField()