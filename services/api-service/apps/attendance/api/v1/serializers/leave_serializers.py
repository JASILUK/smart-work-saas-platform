# =====================================================
# SERIALIZERS
# =====================================================
# apps/leave/serializers.py
# =====================================================

from rest_framework import serializers
from apps.attendance.models.leave import LeaveType, LeaveBalance, LeaveRequest

class LeaveTypeListSerializer(serializers.ModelSerializer):
    """
    Optimized summary list serializer for corporate policy listings.
    """
    class Meta:
        model = LeaveType
        fields = [
            "id", "name", "code", "description", "annual_quota",
            "is_paid", "requires_approval", "allow_half_day", 
            "requires_attachment", "is_active", "created_at"
        ]


class LeaveTypeDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for single resource extraction lookups.
    """
    class Meta:
        model = LeaveType
        fields = [
            "id", "name", "code", "description", "annual_quota",
            "is_paid", "requires_approval", "allow_half_day", 
            "requires_attachment", "is_active", "created_at", "updated_at"
        ]


class LeaveTypeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Write-enabled validation contract mapping incoming payload vectors safely.
    """
    class Meta:
        model = LeaveType
        fields = [
            "name", "code", "description", "annual_quota",
            "is_paid", "requires_approval", "allow_half_day", 
            "requires_attachment", "is_active" # ✅ FIXED: Field explicitly present now
        ]


class LeaveBalanceListSerializer(serializers.ModelSerializer):
    """
    List serializer for LeaveBalance.
    """
    leave_type = LeaveTypeListSerializer(read_only=True)
    employee_name = serializers.CharField(source="membership.user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "leave_year",
            "leave_type",
            "employee_name",
            "department_name",
            "allocated_days",
            "used_days",
            "remaining_days",
            "created_at",
        ]


class LeaveBalanceDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer for LeaveBalance.
    """
    leave_type = LeaveTypeDetailSerializer(read_only=True)
    employee_name = serializers.CharField(source="membership.user.get_full_name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "leave_year",
            "leave_type",
            "employee_name",
            "allocated_days",
            "used_days",
            "remaining_days",
            "created_at",
            "updated_at",
        ]


class LeaveBalanceAdjustmentSerializer(serializers.Serializer):
    """
    Serializer for manual balance adjustment.
    """
    adjustment_days = serializers.DecimalField(max_digits=5, decimal_places=1)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveBalanceAllocationSerializer(serializers.Serializer):
    """
    Serializer for yearly balance allocation.
    """
    membership_id = serializers.IntegerField()
    leave_type_id = serializers.IntegerField()
    leave_year = serializers.IntegerField()
    allocated_days = serializers.DecimalField(max_digits=5, decimal_places=1)


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """
    List serializer for LeaveRequest.
    """
    leave_type = LeaveTypeListSerializer(read_only=True)
    employee_name = serializers.CharField(source="membership.user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", read_only=True)
    approver_name = serializers.CharField(source="approved_by.user.get_full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "status",
            "leave_type",
            "employee_name",
            "department_name",
            "start_date",
            "end_date",
            "total_days",
            "is_half_day",
            "half_day_session",
            "reason",
            "approver_name",
            "approved_at",
            "rejection_reason",
            "created_at",
        ]


class LeaveRequestDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer for LeaveRequest.
    """
    leave_type = LeaveTypeDetailSerializer(read_only=True)
    employee_name = serializers.CharField(source="membership.user.username", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", read_only=True)
    approver_name = serializers.CharField(source="approved_by.user.username", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "status",
            "leave_type",
            "employee_name",
            "department_name",
            "start_date",
            "end_date",
            "total_days",
            "is_half_day",
            "half_day_session",
            "reason",
            "attachment",
            "approved_by",
            "approver_name",
            "approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    """
    Create serializer for LeaveRequest.
    """
    leave_type_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.ChoiceField(
        choices=LeaveRequest.HalfDaySession.choices,
        required=False,
        allow_blank=True,
    )
    reason = serializers.CharField()
    attachment = serializers.FileField(required=False, allow_null=True)


class LeaveRequestApproveSerializer(serializers.Serializer):
    """
    Approve serializer for LeaveRequest.
    """
    pass


class LeaveRequestRejectSerializer(serializers.Serializer):
    """
    Reject serializer for LeaveRequest.
    """
    rejection_reason = serializers.CharField(required=True)


class LeaveRequestCancelSerializer(serializers.Serializer):
    """
    Cancel serializer for LeaveRequest.
    """
    pass


class LeaveRequestStatisticsSerializer(serializers.Serializer):
    """
    Statistics serializer for HR dashboard.
    """
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    today = serializers.IntegerField()
    this_month = serializers.IntegerField()
    total_days_approved = serializers.DecimalField(max_digits=10, decimal_places=1)


class LeaveRequestPaginatedResponseSerializer(serializers.Serializer):
    """
    Paginated response including statistics.
    """
    statistics = LeaveRequestStatisticsSerializer()
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = LeaveRequestListSerializer(many=True)

