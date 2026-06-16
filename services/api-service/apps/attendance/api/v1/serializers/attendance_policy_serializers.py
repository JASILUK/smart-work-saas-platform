from rest_framework import serializers
from apps.attendance.models import AttendancePolicy


# =====================================================
# 1. ATTENDANCE POLICY SERIALIZER
# =====================================================

class AttendancePolicySerializer(serializers.ModelSerializer):
    """
    Provides a comprehensive, read-only serialization blueprint designed
    to represent a company's systemic compliance and clock-interpretation rules.
    """
    company = serializers.IntegerField(source="company.id", read_only=True)
    updated_at = serializers.DateTimeField(source="modified", read_only=True)

    class Meta:
        model = AttendancePolicy
        fields = [
            "company",
            "required_work_minutes",
            "half_day_below_minutes",
            "late_after_minutes",
            "early_exit_before_minutes",
            "overtime_enabled",
            "overtime_after_minutes",
            "auto_absent_if_no_checkin",
            "count_weekend_as_overtime",
            "attendance_regularization_enabled",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# =====================================================
# 2. ATTENDANCE POLICY UPDATE SERIALIZER
# =====================================================

class AttendancePolicyUpdateSerializer(serializers.ModelSerializer):
    """
    Validates mutation payloads for creation (POST) and partial updates (PATCH)
    targeted against tenant-level workflow interpretation policies.
    """
    required_work_minutes = serializers.IntegerField(required=False)
    half_day_below_minutes = serializers.IntegerField(required=False)
    late_after_minutes = serializers.IntegerField(required=False)
    early_exit_before_minutes = serializers.IntegerField(required=False)
    overtime_enabled = serializers.BooleanField(required=False)
    overtime_after_minutes = serializers.IntegerField(required=False)
    auto_absent_if_no_checkin = serializers.BooleanField(required=False)
    count_weekend_as_overtime = serializers.BooleanField(required=False)
    attendance_regularization_enabled = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = AttendancePolicy
        fields = [
            "required_work_minutes",
            "half_day_below_minutes",
            "late_after_minutes",
            "early_exit_before_minutes",
            "overtime_enabled",
            "overtime_after_minutes",
            "auto_absent_if_no_checkin",
            "count_weekend_as_overtime",
            "attendance_regularization_enabled",
            "is_active",
        ]

    # =====================================================
    # FIELD-LEVEL VALIDATIONS
    # =====================================================

    def validate_required_work_minutes(self, value: int) -> int:
        """Enforces positive parameter requirements for mandatory shift ranges."""
        if value <= 0:
            raise serializers.ValidationError("Required work minutes must be greater than zero.")
        return value

    def validate_half_day_below_minutes(self, value: int) -> int:
        """Enforces positive parameter requirements for partial breakdown metrics."""
        if value <= 0:
            raise serializers.ValidationError("Half day threshold minutes must be greater than zero.")
        return value

    def validate_late_after_minutes(self, value: int) -> int:
        """Ensures arrival grace windows do not register negative thresholds."""
        if value < 0:
            raise serializers.ValidationError("Late arrival grace minutes cannot be negative.")
        return value

    def validate_early_exit_before_minutes(self, value: int) -> int:
        """Ensures departure grace windows do not register negative thresholds."""
        if value < 0:
            raise serializers.ValidationError("Early departure margin minutes cannot be negative.")
        return value

    def validate_overtime_after_minutes(self, value: int) -> int:
        """Enforces positive parameters for the overtime calculation floor."""
        if value <= 0:
            raise serializers.ValidationError("Overtime calculation threshold must be greater than zero.")
        return value

    # =====================================================
    # CROSS-FIELD VALIDATION
    # =====================================================

    def validate(self, attrs: dict) -> dict:
        """
        Evaluates interconnected threshold matrix parameters.
        Uses existing model instance flags as fallback layers during dynamic context evaluations.
        """
        # Resolve target states by reviewing patch inputs against instance fallback configurations
        has_instance = self.instance is not None
        
        required_work = attrs.get(
            "required_work_minutes", 
            getattr(self.instance, "required_work_minutes", 480) if has_instance else 480
        )
        half_day = attrs.get(
            "half_day_below_minutes", 
            getattr(self.instance, "half_day_below_minutes", 240) if has_instance else 240
        )
        overtime_enabled = attrs.get(
            "overtime_enabled", 
            getattr(self.instance, "overtime_enabled", False) if has_instance else False
        )
        overtime_after = attrs.get(
            "overtime_after_minutes", 
            getattr(self.instance, "overtime_after_minutes", 480) if has_instance else 480
        )

        # 1. Core structural verification: Half-day limits cannot encroach upon full-day milestones
        if half_day >= required_work:
            raise serializers.ValidationError({
                "half_day_below_minutes": "Half day threshold parameters must be less than the total required work minutes."
            })

        # 2. Roster rule verification: Active overtime accumulation cannot begin before normal work shifts are met
        if overtime_enabled and overtime_after < required_work:
            raise serializers.ValidationError({
                "overtime_after_minutes": "When overtime tracking is active, the calculation threshold must match or exceed required work minutes."
            })

        return attrs