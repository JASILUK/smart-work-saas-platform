from rest_framework import serializers
from apps.attendance.models import Shift, EmployeeShiftAssignment
from apps.companies.models import Membership


# =====================================================
# NESTED MEMBERSHIP SERIALIZER
# =====================================================

class NestedMembershipSerializer(serializers.ModelSerializer):
    """
    Provides a minimal representation of an employee or corporate actor,
    exposing basic account credentials without relational leaking.
    """
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "username",
        ]
        read_only_fields = fields


# =====================================================
# NESTED SHIFT SERIALIZER
# =====================================================

class NestedShiftSerializer(serializers.ModelSerializer):
    """
    Provides a streamlined, read-only baseline structure of a work schedule profile
    suitable for injection into timeline listings.
    """
    class Meta:
        model = Shift
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "is_night_shift",
        ]
        read_only_fields = fields


# =====================================================
# EMPLOYEE SHIFT ASSIGNMENT LIST SERIALIZER
# =====================================================

class EmployeeShiftAssignmentListSerializer(serializers.ModelSerializer):
    """
    Used for parsing massive assignment data arrays efficiently inside management grids,
    utilizing nested read-only relational footprints.
    """
    membership = NestedMembershipSerializer(read_only=True)
    shift = NestedShiftSerializer(read_only=True)
    effective_to = serializers.DateField(source="effective_until", read_only=True)

    class Meta:
        model = EmployeeShiftAssignment
        fields = [
            "id",
            "membership",
            "shift",
            "effective_from",
            "effective_to",
            "is_active",
        ]
        read_only_fields = fields


# =====================================================
# EMPLOYEE SHIFT ASSIGNMENT DETAIL SERIALIZER
# =====================================================

class EmployeeShiftAssignmentDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive, audit-grade details serialization configuration mapping 
    chronological updates and workflow assignees.
    """
    membership = NestedMembershipSerializer(read_only=True)
    shift = NestedShiftSerializer(read_only=True)
    assigned_by = NestedMembershipSerializer(read_only=True)
    effective_to = serializers.DateField(source="effective_until", read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(source="modified", read_only=True)

    class Meta:
        model = EmployeeShiftAssignment
        fields = [
            "id",
            "membership",
            "shift",
            "effective_from",
            "effective_to",
            "assigned_by",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# =====================================================
# EMPLOYEE SHIFT ASSIGNMENT CREATE SERIALIZER
# =====================================================

class EmployeeShiftAssignmentCreateSerializer(serializers.ModelSerializer):
    """
    Validates structural tracking properties when onboarding or setting an active worker
    onto a specific corporate shift schedule.
    """
    effective_to = serializers.DateField(
        source="effective_until", 
        required=False, 
        allow_null=True, 
        default=None
    )
    notes = serializers.CharField(
        required=False, 
        allow_blank=True, 
        default=""
    )

    class Meta:
        model = EmployeeShiftAssignment
        fields = [
            "membership",
            "shift",
            "effective_from",
            "effective_to",
            "notes",
        ]

    def validate(self, attrs: dict) -> dict:
        """Evaluates timeline range constraints to prevent retrofitted tracking anomalies."""
        effective_from = attrs.get("effective_from")
        # Read directly from mapped model field reference string targets
        effective_until = attrs.get("effective_until")

        if effective_until and effective_until < effective_from:
            raise serializers.ValidationError(
                {"effective_to": "Effective end date must be after effective start date."}
            )

        return attrs


# =====================================================
# EMPLOYEE SHIFT ASSIGNMENT UPDATE SERIALIZER
# =====================================================

class EmployeeShiftAssignmentUpdateSerializer(serializers.ModelSerializer):
    """
    Validates payload parameters for partial mutations (PATCH requests) against 
    existing timelines, enforcing date logic rules via context fallbacks.
    """
    shift = serializers.PrimaryKeyRelatedField(queryset=Shift.objects.all(), required=False)
    effective_from = serializers.DateField(required=False)
    effective_to = serializers.DateField(source="effective_until", required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = EmployeeShiftAssignment
        fields = [
            "shift",
            "effective_from",
            "effective_to",
            "notes",
        ]

    def validate(self, attrs: dict) -> dict:
        """Evaluates prospective timeline updates utilizing existing model row vectors as fallbacks."""
        # Use existing model values as safe fallbacks if properties are missing from partial payloads
        effective_from = attrs.get("effective_from", getattr(self.instance, "effective_from"))
        
        # Pull parameters safely via source tracking names or original fields mapping matrix
        if "effective_until" in attrs:
            effective_until = attrs["effective_until"]
        else:
            effective_until = getattr(self.instance, "effective_until", None)

        if effective_until and effective_until < effective_from:
            raise serializers.ValidationError(
                {"effective_to": "Effective end date must be after effective start date."}
            )

        return attrs