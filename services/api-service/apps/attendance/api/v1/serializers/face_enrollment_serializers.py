from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy
from apps.attendance.models.face_enrollment import FaceEnrollment
from apps.attendance.validators.face_enrollment_validator import FaceEnrollmentValidator


# ─────────────────────────────────────────────────────────────────────────────
# Region: Policy Configurations Serializers
# ─────────────────────────────────────────────────────────────────────────────

class CompanyFaceEnrollmentPolicyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyFaceEnrollmentPolicy
        fields = ["id", "policy_type", "is_active", "created_at", "updated_at"]
        read_only_fields = fields


class CompanyFaceEnrollmentPolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyFaceEnrollmentPolicy
        fields = ["policy_type", "is_active"]


# ─────────────────────────────────────────────────────────────────────────────
# Region: Face Enrollment Lifecycle Serializers
# ─────────────────────────────────────────────────────────────────────────────

class FaceEnrollmentListSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    approver_username = serializers.CharField(source="approved_by.user.username", read_only=True)

    class Meta:
        model = FaceEnrollment
        fields = ["id", "status", "enrollment_source", "employee_username", "liveness_verified", "approver_username", "approved_at", "created_at"]
        read_only_fields = fields


class FaceEnrollmentDetailSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    employee_email = serializers.CharField(source="membership.user.email", read_only=True)
    approver_username = serializers.CharField(source="approved_by.user.username", read_only=True)
    revoker_username = serializers.CharField(source="revoked_by.user.username", read_only=True)

    class Meta:
        model = FaceEnrollment
        fields = [
            "id", "status", "enrollment_source", "employee_username", "employee_email",
            "embedding_version", "similarity_threshold", "liveness_verified",
            "approver_username", "approved_at", "rejection_reason",
            "revoker_username", "revoked_at", "revocation_reason", "created_at", "updated_at"
        ]
        read_only_fields = fields


class FaceEnrollmentCreateSerializer(serializers.Serializer):
    # Write-only vector coordinates array mapping. Never returned or exposed in read responses.
    embedding = serializers.ListField(
        child=serializers.FloatField(),
        write_only=True,
        required=True
    )

    def validate_embedding(self, value):
        FaceEnrollmentValidator.validate_embedding_structure(value)
        return value


class FaceEnrollmentApproveSerializer(serializers.Serializer):
    pass  # Payload free action trigger confirmation processing enclosure


class FaceEnrollmentRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class FaceEnrollmentRevokeSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)