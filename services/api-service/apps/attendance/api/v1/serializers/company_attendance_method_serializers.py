from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.validators.company_attendance_method_validator import CompanyAttendanceMethodValidator


class CompanyAttendanceMethodDetailSerializer(serializers.ModelSerializer):
    """
    Read-only detailed serializer for organizational allowed validation parameters.
    """
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = CompanyAttendanceMethod
        fields = [
            "id",
            "method",
            "method_display",
            "is_active",
            "created_at",
            "updated_at"
        ]
        read_only_fields = fields


class CompanyAttendanceMethodReplaceSerializer(serializers.Serializer):
    """
    Validates incoming array tracking schema switches.
    Applies strict multi-tenant validation boundaries to ensure system consistency.
    """
    methods = serializers.ListField(
        child=serializers.CharField(max_length=30),
        required=True,
        allow_empty=False,
        error_messages={
            "required": _("The configuration tracking array block field 'methods' is required."),
            "empty": _("Tenant verification structures require at least one active ingestion method.")
        }
    )

    def validate_methods(self, value: list) -> list:
        # Business Rule 3: Automatically deduplicate input array parameters
        cleaned_methods = [str(item).strip().upper() for item in value if item]
        unique_methods = list(dict.fromkeys(cleaned_methods))

        if not unique_methods:
            raise serializers.ValidationError(
                _("Tenant structural synchronization pipelines require a valid target matrix payload.")
            )

        # Structural Layer: Cross-reference values against registered model choices
        for method in unique_methods:
            CompanyAttendanceMethodValidator.validate_method(method)

        # Business Rule 2: Prevent the MANUAL method from being configured by itself
        if unique_methods == [CompanyAttendanceMethod.AttendanceMethodChoices.MANUAL]:
            raise serializers.ValidationError(
                _("The 'MANUAL' adjustment strategy cannot be deployed alone. Provide an employee-facing log method.")
            )

        return unique_methods