from rest_framework import serializers


class DailyAttendanceListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    attendance_date = serializers.DateField(read_only=True)
    attendance_status = serializers.CharField(read_only=True)
    first_check_in_at = serializers.CharField(read_only=True, allow_null=True)
    last_check_out_at = serializers.CharField(read_only=True, allow_null=True)
    total_work_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    late_minutes = serializers.IntegerField(read_only=True)
    attendance_method_summary = serializers.CharField(read_only=True, allow_blank=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)


class DailyAttendanceDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    attendance_date = serializers.DateField(read_only=True)
    attendance_status = serializers.CharField(read_only=True)
    first_check_in_at = serializers.CharField(read_only=True, allow_null=True)
    last_check_out_at = serializers.CharField(read_only=True, allow_null=True)
    total_work_minutes = serializers.IntegerField(read_only=True)
    total_break_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    late_minutes = serializers.IntegerField(read_only=True)
    early_exit_minutes = serializers.IntegerField(read_only=True)
    required_work_minutes = serializers.IntegerField(read_only=True)
    attendance_method_summary = serializers.CharField(read_only=True, allow_blank=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)
    is_absent = serializers.BooleanField(read_only=True)
    is_early_exit = serializers.BooleanField(read_only=True)
    is_auto_closed = serializers.BooleanField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    review_reason = serializers.CharField(read_only=True, allow_blank=True)
    auto_close_reason = serializers.CharField(read_only=True, allow_blank=True)
    schedule_snapshot = serializers.JSONField(read_only=True)
    policy_snapshot = serializers.JSONField(read_only=True)
    source = serializers.CharField(read_only=True)
    finalized_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AttendanceTimelineSerializer(serializers.Serializer):
    event_type = serializers.CharField(read_only=True)
    event_time = serializers.CharField(read_only=True)
    attendance_method = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True, allow_null=True)
    notes = serializers.CharField(read_only=True, allow_blank=True)


class AttendanceSummarySerializer(serializers.Serializer):
    total_days = serializers.IntegerField(read_only=True)
    present_days = serializers.IntegerField(read_only=True)
    absent_days = serializers.IntegerField(read_only=True)
    half_days = serializers.IntegerField(read_only=True)
    late_days = serializers.IntegerField(read_only=True)
    leave_days = serializers.IntegerField(read_only=True)
    holiday_days = serializers.IntegerField(read_only=True)
    weekend_days = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    total_work_hours = serializers.FloatField(read_only=True)
    total_overtime_hours = serializers.FloatField(read_only=True)


class AttendanceStatisticsSerializer(serializers.Serializer):
    total_records = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    absent_count = serializers.IntegerField(read_only=True)
    late_count = serializers.IntegerField(read_only=True)
    leave_count = serializers.IntegerField(read_only=True)
    review_required_count = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)


class AttendanceTrendSerializer(serializers.Serializer):
    month = serializers.IntegerField(read_only=True)
    present = serializers.IntegerField(read_only=True)
    absent = serializers.IntegerField(read_only=True)
    late = serializers.IntegerField(read_only=True)
    leave = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)


class AttendanceCalendarSerializer(serializers.Serializer):
    date = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)


class AttendanceDetailResponseSerializer(serializers.Serializer):
    daily_record = DailyAttendanceDetailSerializer(read_only=True)
    timeline = AttendanceTimelineSerializer(many=True, read_only=True)
