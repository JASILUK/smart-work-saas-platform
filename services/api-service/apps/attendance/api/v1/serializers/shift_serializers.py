from typing import Any
from rest_framework import serializers
from apps.attendance.models import Shift


# =====================================================
# 1. SHIFT LIST SERIALIZER
# =====================================================

class ShiftListSerializer(serializers.ModelSerializer):
    """
    Provides a lightweight, read-only serialization layout used to back
    high-level shift inventory grids and operational selector dropdowns.
    """
    public_id = serializers.IntegerField(source="id", read_only=True)
    code = serializers.CharField(source="name", read_only=True)
    shift_type = serializers.SerializerMethodField()
    is_flexible = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = [
            "public_id",
            "name",
            "code",
            "shift_type",
            "start_time",
            "end_time",
            "is_flexible",
            "is_active",
            "is_default",
        ]
        read_only_fields = fields

    def get_shift_type(self, obj: Shift) -> str:
        """Maps internal night-shift booleans to a clear text type label."""
        return "night" if obj.is_night_shift else "regular"

    def get_is_flexible(self, obj: Shift) -> bool:
        """
        Determines if the shift uses a flexible schedule context.
        Since explicit flex hour fields are absent from this schema model,
        we evaluate standard fallback states.
        """
        return False

    def get_is_default(self, obj: Shift) -> bool:
        """Checks reverse foreign key relationships to verify company fallback defaults."""
        return hasattr(obj, "default_work_schedules") and obj.default_work_schedules.exists()


# =====================================================
# 2. SHIFT DETAIL SERIALIZER
# =====================================================

class ShiftDetailSerializer(serializers.ModelSerializer):
    """
    Provides a comprehensive, read-only serialization layout detailing all 
    operational constraints and audit trails assigned to a single shift profile.
    """
    public_id = serializers.IntegerField(source="id", read_only=True)
    code = serializers.CharField(source="name", read_only=True)
    shift_type = serializers.SerializerMethodField()
    is_flexible = serializers.SerializerMethodField()
    core_start_time = serializers.SerializerMethodField()
    core_end_time = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(source="modified", read_only=True)

    class Meta:
        model = Shift
        fields = [
            "public_id",
            "name",
            "code",
            "description",
            "shift_type",
            "start_time",
            "end_time",
            "break_duration_minutes",
            "is_flexible",
            "core_start_time",
            "core_end_time",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_shift_type(self, obj: Shift) -> str:
        """Maps internal night-shift booleans to a clear text type label."""
        return "night" if obj.is_night_shift else "regular"

    def get_is_flexible(self, obj: Shift) -> bool:
        """Baseline structural layout placeholder tracking schedule parameters."""
        return False

    def get_core_start_time(self, obj: Shift) -> Any:
        """Returns baseline start parameters to prevent field layout break exceptions."""
        return None

    def get_core_end_time(self, obj: Shift) -> Any:
        """Returns baseline end parameters to prevent field layout break exceptions."""
        return None

    def get_is_default(self, obj: Shift) -> bool:
        """Evaluates whether this profile maps as the target tenant default selection."""
        return hasattr(obj, "default_work_schedules") and obj.default_work_schedules.exists()


# =====================================================
# 3. SHIFT CREATE SERIALIZER
# =====================================================

class ShiftCreateSerializer(serializers.ModelSerializer):
    """
    Validates incoming payload profiles sent by HR operators when 
    instantiating a reusable work schedule configuration.
    """
    shift_type = serializers.CharField(required=False, default="regular")
    break_duration_minutes = serializers.IntegerField(required=False, default=60)

    class Meta:
        model = Shift
        fields = [
            "name",
            "description",
            "shift_type",
            "start_time",
            "end_time",
            "break_duration_minutes",
            "is_active",
        ]

    def validate_name(self, value: str) -> str:
        """Sanitizes whitespace framing from name strings."""
        return str(value).strip()

    def validate_description(self, value: str) -> str:
        """Sanitizes whitespace framing from descriptive blocks."""
        return str(value).strip() if value else ""

    def validate_break_duration_minutes(self, value: int) -> int:
        """Enforces logical positive parameters for duration values."""
        if value < 0:
            raise serializers.ValidationError("Break duration cannot be negative.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Evaluates model timing constraints and normalizes field types."""
        shift_type = str(attrs.get("shift_type", "regular")).lower()
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        # Set database model boolean states based on string representation fields
        if shift_type == "night":
            attrs["is_night_shift"] = True
        else:
            attrs["is_night_shift"] = False

        # Enforce baseline verification conditions across standard schedule models
        if not start_time or not end_time:
            raise serializers.ValidationError(
                {"start_time": "Standard shift profiles require both start and end times to be specified."}
            )

        # Pop out non-model variables safely to prevent instantiation argument payload crashes
        attrs.pop("shift_type", None)
        return attrs


# =====================================================
# 4. SHIFT UPDATE SERIALIZER
# =====================================================

class ShiftUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial, patch-driven parameter updates targeted against 
    pre-existing schedule configurations.
    """
    name = serializers.CharField(required=False)
    shift_type = serializers.CharField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    break_duration_minutes = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Shift
        fields = [
            "name",
            "description",
            "shift_type",
            "start_time",
            "end_time",
            "break_duration_minutes",
            "is_active",
        ]

    def validate_name(self, value: str) -> str:
        """Sanitizes whitespace framing from name strings if supplied."""
        return str(value).strip()

    def validate_description(self, value: str) -> str:
        """Sanitizes whitespace framing from descriptive blocks if supplied."""
        return str(value).strip() if value else ""

    def validate_break_duration_minutes(self, value: int) -> int:
        """Enforces logical positive parameters for duration values if supplied."""
        if value < 0:
            raise serializers.ValidationError("Break duration cannot be negative.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Evaluates field transformations against pre-existing instance attributes for updates."""
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if "shift_type" in attrs:
            if str(attrs["shift_type"]).lower() == "night":
                attrs["is_night_shift"] = True
            else:
                attrs["is_night_shift"] = False
            attrs.pop("shift_type", None)

        if start_time is None or end_time is None:
            raise serializers.ValidationError(
                {"start_time": "Standard shift configurations require both start and end times to be specified."}
            )

        return attrs