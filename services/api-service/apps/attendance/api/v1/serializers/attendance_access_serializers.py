from rest_framework import serializers
from apps.companies.models import Department, Membership
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from apps.attendance.api.v1.serializers.company_attendance_method_serializers import CompanyAttendanceMethodDetailSerializer
from apps.attendance.api.v1.serializers.attendance_location_serializers import AttendanceLocationListSerializer


# ─────────────────────────────────────────────────────────────────────────────
# Region: Sub-Nested Informational Elements
# ─────────────────────────────────────────────────────────────────────────────

class MembershipMinimalSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "username", "email", "job_title", "work_mode"]


class DepartmentMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


# ─────────────────────────────────────────────────────────────────────────────
# Region: Entity 1 - Company Defaults
# ─────────────────────────────────────────────────────────────────────────────

class CompanyAttendanceDefaultDetailSerializer(serializers.ModelSerializer):
    allowed_methods = CompanyAttendanceMethodDetailSerializer(many=True, read_only=True)
    allowed_locations = AttendanceLocationListSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyAttendanceDefault
        fields = ["id", "validation_mode", "is_active", "allowed_methods", "allowed_locations", "created_at", "updated_at"]


class CompanyAttendanceDefaultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyAttendanceDefault
        fields = ["validation_mode", "is_active", "allowed_methods", "allowed_locations"]


# ─────────────────────────────────────────────────────────────────────────────
# Region: Entity 2 - Access Group Rules
# ─────────────────────────────────────────────────────────────────────────────

class AttendanceAccessRuleListSerializer(serializers.ModelSerializer):
    # ✅ FIX: Include relational detail mappings directly in the list payload
    allowed_methods = CompanyAttendanceMethodDetailSerializer(many=True, read_only=True)
    allowed_locations = AttendanceLocationListSerializer(many=True, read_only=True)
    department = DepartmentMinimalSerializer(read_only=True)

    class Meta:
        model = AttendanceAccessRule
        fields = [
            "id", "name", "scope_type", "work_mode", "department", 
            "validation_mode", "priority", "is_active", 
            "allowed_methods", "allowed_locations" # 👈 Add these fields here!
        ]
        

class AttendanceAccessRuleDetailSerializer(serializers.ModelSerializer):
    allowed_methods = CompanyAttendanceMethodDetailSerializer(many=True, read_only=True)
    allowed_locations = AttendanceLocationListSerializer(many=True, read_only=True)
    department = DepartmentMinimalSerializer(read_only=True)

    class Meta:
        model = AttendanceAccessRule
        fields = [
            "id", "name", "scope_type", "work_mode", "department", 
            "validation_mode", "priority", "is_active", "allowed_methods", 
            "allowed_locations", "created_at", "updated_at"
        ]


class AttendanceAccessRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceAccessRule
        fields = [
            "name", "scope_type", "work_mode", "department", 
            "validation_mode", "priority", "is_active", "allowed_methods", 
            "allowed_locations"
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Region: Entity 3 - Employee Specific Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeAttendanceOverrideListSerializer(serializers.ModelSerializer):
    # ✅ FIXED: Provide nested relationship objects directly to the dashboard index payload framework array
    allowed_methods = CompanyAttendanceMethodDetailSerializer(many=True, read_only=True)
    allowed_locations = AttendanceLocationListSerializer(many=True, read_only=True)
    membership = MembershipMinimalSerializer(read_only=True)

    class Meta:
        model = EmployeeAttendanceOverride
        fields = [
            "id", "membership", "validation_mode", "reason", 
            "is_active", "allowed_methods", "allowed_locations"
        ]


class EmployeeAttendanceOverrideDetailSerializer(serializers.ModelSerializer):
    allowed_methods = CompanyAttendanceMethodDetailSerializer(many=True, read_only=True)
    allowed_locations = AttendanceLocationListSerializer(many=True, read_only=True)
    membership = MembershipMinimalSerializer(read_only=True)

    class Meta:
        model = EmployeeAttendanceOverride
        fields = [
            "id", "membership", "validation_mode", "reason", "is_active", 
            "allowed_methods", "allowed_locations", "created_at", "updated_at"
        ]


class EmployeeAttendanceOverrideCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAttendanceOverride
        fields = [
            "membership", "validation_mode", "reason", 
            "is_active", "allowed_methods", "allowed_locations"
        ]

# ─────────────────────────────────────────────────────────────────────────────
# Region: Core Resolution Outputs Shape
# ─────────────────────────────────────────────────────────────────────────────

class ResolvedLocationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    radius_meters = serializers.IntegerField()


class AttendanceAccessResolutionSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=["override", "rule", "default"])
    validation_mode = serializers.CharField()
    methods = serializers.ListField(child=serializers.CharField())
    locations = ResolvedLocationSerializer(many=True)