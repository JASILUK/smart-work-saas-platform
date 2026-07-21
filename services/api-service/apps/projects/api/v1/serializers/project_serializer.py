import re
from typing import Any, Dict, List, Optional

from apps.companies.models import Membership
from rest_framework import serializers

from apps.projects.models.projects import Project
from apps.projects.models.project_members import ProjectMember
from apps.projects.selectors.project_selector import ProjectSelector


# ================================================================
# NESTED INPUT SERIALIZERS
# ================================================================

class ProjectMemberInputSerializer(serializers.Serializer):
    """
    Input-only serializer for project member creation data.
    """

    membership_id = serializers.IntegerField(
        min_value=1,
        help_text="Membership ID of the employee to add.",
    )

    role = serializers.ChoiceField(
        choices=ProjectMember.Role.choices,
        help_text="Project role for the member.",
    )

    class Meta:
        fields = ["membership_id", "role"]


# ================================================================
# WRITE SERIALIZERS
# ================================================================

class ProjectCreateSerializer(serializers.Serializer):
    """
    Serializer for project creation.
    """

    name = serializers.CharField(
        max_length=255,
        help_text="Display name of the project.",
    )

    code = serializers.CharField(
        max_length=50,
        help_text="Unique identifier within the company (e.g., PROJ-001).",
    )

    description = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        help_text="Detailed description of the project scope and goals.",
    )

    visibility = serializers.ChoiceField(
        choices=Project.Visibility.choices,
        default=Project.Visibility.PRIVATE,
        help_text="Project visibility: public or private.",
    )

    status = serializers.ChoiceField(
        choices=Project.Status.choices,
        default=Project.Status.PLANNING,
        required=False,
        help_text="Current lifecycle state of the project (defaults to planning).",
    )

    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Planned or actual start date.",
    )

    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Planned or actual end date.",
    )

    color = serializers.CharField(
        max_length=7,
        default="#6366F1",
        help_text="Hex color for visual identification (e.g., #6366F1).",
    )

    client_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Primary contact person at the client organization.",
    )

    client_company = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the external client company.",
    )

    client_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Email address of the client contact.",
    )

    client_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text="Phone number of the client contact.",
    )

    owner_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        help_text="Optional project owner ID. Automatically defaults to creator.",
    )

    members = ProjectMemberInputSerializer(
        many=True,
        required=False,
        help_text="Optional list of initial project members.",
    )

    def validate_color(self, value: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError(
                "Color must be a valid hex code (e.g., #6366F1)."
            )
        return value

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        return data


class ProjectUpdateSerializer(serializers.Serializer):
    """
    Serializer for project updates.
    """

    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Display name of the project.",
    )

    description = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        help_text="Detailed description of the project scope and goals.",
    )

    visibility = serializers.ChoiceField(
        choices=Project.Visibility.choices,
        required=False,
        help_text="Project visibility: public or private.",
    )

    status = serializers.ChoiceField(
        choices=Project.Status.choices,
        required=False,
        help_text="Current lifecycle state of the project.",
    )

    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Planned or actual start date.",
    )

    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Planned or actual end date.",
    )

    color = serializers.CharField(
        max_length=7,
        required=False,
        help_text="Hex color for visual identification (e.g., #6366F1).",
    )

    client_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Primary contact person at the client organization.",
    )

    client_company = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the external client company.",
    )

    client_email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Email address of the client contact.",
    )

    client_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        help_text="Phone number of the client contact.",
    )

    owner_id = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="Membership ID of the project owner.",
    )

    def validate_color(self, value: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError(
                "Color must be a valid hex code (e.g., #6366F1)."
            )
        return value

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        return data


class ProjectArchiveSerializer(serializers.Serializer):
    """
    Minimal serializer for project archive action.
    """

    archive_reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for archiving the project.",
    )


class ProjectRestoreSerializer(serializers.Serializer):
    """
    Minimal serializer for project restore action.
    """

    restore_reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for restoring the project.",
    )


# ================================================================
# READ SERIALIZERS
# ================================================================
class ProjectOwnerSerializer(serializers.Serializer):
    """
    Lightweight nested serializer for project owner (Membership) display.
    Expects a Membership instance as input object.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    job_title = serializers.CharField(read_only=True, allow_null=True)

    def get_name(self, obj: Membership) -> str:
        """
        Safely resolve display name from user's full name, username, or email.
        """
        if not obj or not getattr(obj, "user", None):
            return ""
        
        user = obj.user
        full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        return full_name.strip() or getattr(user, "username", "") or user.email

    def get_email(self, obj: Membership) -> str:
        """
        Prefer workspace email if set, otherwise fallback to account user email.
        """
        if not obj:
            return ""
        return obj.work_space_email or (obj.user.email if hasattr(obj, "user") else "")


class ProjectListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for enterprise project list dashboards.
    """

    is_active = serializers.BooleanField(read_only=True)
    is_archived = serializers.BooleanField(read_only=True)

    member_count = serializers.IntegerField(read_only=True, default=0)
    task_count = serializers.IntegerField(read_only=True, default=0)
    completed_task_count = serializers.IntegerField(read_only=True, default=0)
    progress_percentage = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "code",
            "status",
            "visibility",
            "color",
            "owner",
            "start_date",
            "end_date",
            "is_active",
            "is_archived",
            "member_count",
            "task_count",
            "completed_task_count",
            "progress_percentage",
            "created_at",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    Complete serializer for Project Overview Tab / Workspace Detail API.
    """

    owner = ProjectOwnerSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_archived = serializers.BooleanField(read_only=True)

    member_summary = serializers.SerializerMethodField(read_only=True)
    task_summary = serializers.SerializerMethodField(read_only=True)
    meeting_summary = serializers.SerializerMethodField(read_only=True)
    file_summary = serializers.SerializerMethodField(read_only=True)
    activity_summary = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = [
            # Core
            "id",
            "name",
            "code",
            "description",
            "color",
            # Visibility & Status
            "visibility",
            "status",
            "is_active",
            "is_archived",
            # Ownership
            "owner",
            # Summaries
            "member_summary",
            "task_summary",
            "meeting_summary",
            "file_summary",
            "activity_summary",
            # Client Info
            "client_name",
            "client_company",
            "client_email",
            "client_phone",
            # Timelines
            "start_date",
            "end_date",
            # Audit Trail
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "archived_at",
        ]
        read_only_fields = [
            "id",
            "code",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "archived_at",
            "is_active",
            "is_archived",
        ]

    def get_member_summary(self, obj: Project) -> Dict[str, int]:
        return ProjectSelector.get_member_summary(obj)

    def get_task_summary(self, obj: Project) -> Dict[str, Any]:
        return ProjectSelector.get_task_summary(obj)

    def get_meeting_summary(self, obj: Project) -> Dict[str, int]:
        return ProjectSelector.get_meeting_summary(obj)

    def get_file_summary(self, obj: Project) -> Dict[str, int]:
        return ProjectSelector.get_file_summary(obj)

    def get_activity_summary(self, obj: Project) -> Dict[str, Any]:
        return ProjectSelector.get_activity_summary(obj)