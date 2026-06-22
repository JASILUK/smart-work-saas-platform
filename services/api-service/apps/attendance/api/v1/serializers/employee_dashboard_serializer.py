from rest_framework import serializers

class EmployeeSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)


class ShiftDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    start = serializers.CharField(read_only=True, allow_blank=True)
    end = serializers.CharField(read_only=True, allow_blank=True)


class TodayStatusSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)
    check_in = serializers.CharField(read_only=True, allow_blank=True)
    check_out = serializers.CharField(read_only=True, allow_blank=True)
    working_minutes = serializers.IntegerField(read_only=True)
    shift = ShiftDetailsSerializer(read_only=True, allow_null=True)


class AttendanceAccessSerializer(serializers.Serializer):
    auto_synced = serializers.BooleanField(read_only=True)
    primary_method = serializers.CharField(read_only=True, allow_null=True)
    available_methods = serializers.ListField(child=serializers.CharField(), read_only=True)
    gps_required = serializers.BooleanField(read_only=True)
    face_enrollment_status = serializers.CharField(read_only=True)


class ActionMatrixSerializer(serializers.Serializer):
    can_check_in = serializers.BooleanField(read_only=True)
    can_check_out = serializers.BooleanField(read_only=True)
    can_start_break = serializers.BooleanField(read_only=True)
    can_resume_break = serializers.BooleanField(read_only=True)


class MonthlySummarySerializer(serializers.Serializer):
    present_days = serializers.IntegerField(read_only=True)
    late_days = serializers.IntegerField(read_only=True)
    absent_days = serializers.IntegerField(read_only=True)
    overtime_hours = serializers.FloatField(read_only=True)


class PendingRequestsSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    items = serializers.ListField(read_only=True)


class LeaveBalanceSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(read_only=True)
    balances = serializers.ListField(read_only=True)


class UpcomingHolidaySerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    date = serializers.CharField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)


class UpcomingShiftSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    start = serializers.CharField(read_only=True)
    end = serializers.CharField(read_only=True)
    effective_from = serializers.CharField(read_only=True)


class UpcomingMetricsSerializer(serializers.Serializer):
    next_holiday = UpcomingHolidaySerializer(read_only=True, allow_null=True)
    next_shift = UpcomingShiftSerializer(read_only=True, allow_null=True)


class EmployeeDashboardSerializer(serializers.Serializer):
    employee = EmployeeSerializer(read_only=True)
    today = TodayStatusSerializer(read_only=True)
    attendance_access = AttendanceAccessSerializer(read_only=True)
    actions = ActionMatrixSerializer(read_only=True)
    monthly_summary = MonthlySummarySerializer(read_only=True)
    pending_requests = PendingRequestsSerializer(read_only=True)
    leave_balance = LeaveBalanceSerializer(read_only=True)
    upcoming = UpcomingMetricsSerializer(read_only=True)

    def create(self, validated_data):
        raise NotImplementedError("Dashboard aggregates do not support mutation vectors.")

    def update(self, instance, validated_data):
        raise NotImplementedError("Dashboard aggregates do not support mutation vectors.")