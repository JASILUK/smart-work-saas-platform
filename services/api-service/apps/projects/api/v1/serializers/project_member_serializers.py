from typing import Any, Dict, List, Optional
from rest_framework import serializers

from apps.projects.models.project_members import ProjectMember
from apps.projects.services.project_member_service import ProjectMemberService


# ================================================================
# NESTED SERIALIZERS
# ================================================================

class MembershipSummarySerializer(serializers.Serializer):
    """
    Lightweight read-only serializer for Membership display.
    """

    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    job_title = serializers.CharField(read_only=True)
    department = serializers.SerializerMethodField(read_only=True)
    work_mode = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "job_title",
            "department",
            "work_mode",
            "is_active",
        ]

    def get_full_name(self, obj) -> str:
        if hasattr(obj, "user") and obj.user:
            return obj.user.get_full_name() or obj.user.email
        return ""

    def get_department(self, obj) -> Optional[str]:
        if hasattr(obj, "department") and obj.department:
            return obj.department.name
        return None


class ProjectSummarySerializer(serializers.Serializer):
    """
    Lightweight read-only serializer for Project display.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    visibility = serializers.CharField(read_only=True)

    class Meta:
        fields = ["id", "name", "code", "status", "visibility"]


# ================================================================
# READ SERIALIZERS
# ================================================================

class ProjectMemberListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for project member list endpoints.
    """

    membership = MembershipSummarySerializer(read_only=True)
    added_by = MembershipSummarySerializer(read_only=True)
    is_owner = serializers.BooleanField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)
    is_member = serializers.BooleanField(read_only=True)
    can_manage_members = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "role",
            "notes",
            "joined_at",
            "is_owner",
            "is_manager",
            "is_member",
            "can_manage_members",
            "membership",
            "added_by",
        ]
        read_only_fields = fields


class ProjectMemberDetailSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for project member detail endpoints.
    """

    membership = MembershipSummarySerializer(read_only=True)
    added_by = MembershipSummarySerializer(read_only=True)
    project = ProjectSummarySerializer(read_only=True)
    company = serializers.SerializerMethodField(read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    added_by_name = serializers.SerializerMethodField(read_only=True)
    can_manage_members = serializers.BooleanField(read_only=True)
    is_owner = serializers.BooleanField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)
    is_member = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "role",
            "notes",
            "joined_at",
            "created_at",
            "updated_at",
            "is_owner",
            "is_manager",
            "is_member",
            "can_manage_members",
            "membership",
            "project",
            "company",
            "project_name",
            "project_code",
            "added_by",
            "added_by_name",
        ]
        read_only_fields = fields

    def get_company(self, obj) -> Optional[Dict[str, Any]]:
        if hasattr(obj.project, "company") and obj.project.company:
            return {
                "id": obj.project.company.id,
                "name": obj.project.company.name,
            }
        return None

    def get_added_by_name(self, obj) -> str:
        if obj.added_by and hasattr(obj.added_by, "user") and obj.added_by.user:
            return obj.added_by.user.get_full_name() or obj.added_by.user.email
        return ""


# ================================================================
# WRITE SERIALIZERS
# ================================================================

class ProjectMemberCreateSerializer(serializers.Serializer):
    """
    Write serializer for adding a single member to a project.
    """

    membership_id = serializers.IntegerField(
        min_value=1,
        help_text="Membership ID of the employee to add.",
    )
    role = serializers.ChoiceField(
        choices=ProjectMember.Role.choices,
        default=ProjectMember.Role.MEMBER,
        help_text="Project role for the new member.",
    )
    notes = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional notes about this membership.",
    )

    def create(self, validated_data: Dict[str, Any]) -> ProjectMember:
        project_id = self.context.get("project_id")
        company = self.context.get("company")
        actor_membership_id = self.context.get("actor_membership_id")

        if not all([project_id, company, actor_membership_id]):
            raise serializers.ValidationError(
                {"context": "Missing required context: project_id, company, or actor."}
            )

        return ProjectMemberService.add_member(
            project_id=project_id,
            company_id=company.id,
            membership_id=validated_data["membership_id"],
            role=validated_data.get("role", ProjectMember.Role.MEMBER),
            notes=validated_data.get("notes"),
            actor_membership_id=actor_membership_id,
        )


class ProjectMemberInputSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(
        min_value=1,
        help_text="Membership ID of the employee to add.",
    )
    role = serializers.ChoiceField(
        choices=ProjectMember.Role.choices,
        default=ProjectMember.Role.MEMBER,
        help_text="Project role for the new member.",
    )
    notes = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional notes about this membership.",
    )


class ProjectMemberBulkCreateSerializer(serializers.Serializer):
    members = ProjectMemberInputSerializer(
        many=True,
        help_text="List of members to add (max 100).",
    )

    def validate_members(self, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(value) > 100:
            raise serializers.ValidationError(
                "Cannot add more than 100 members at once."
            )
        return value

    def create(self, validated_data: Dict[str, Any]) -> List[ProjectMember]:
        project_id = self.context.get("project_id")
        company = self.context.get("company")
        actor_membership_id = self.context.get("actor_membership_id")

        if not all([project_id, company, actor_membership_id]):
            raise serializers.ValidationError(
                {"context": "Missing required context."}
            )

        members = [
            {
                "membership_id": m["membership_id"],
                "role": m.get("role", ProjectMember.Role.MEMBER),
                "notes": m.get("notes"),
            }
            for m in validated_data["members"]
        ]

        return ProjectMemberService.bulk_add_members(
            project_id=project_id,
            company_id=company.id,
            members=members,
            actor_membership_id=actor_membership_id,
        )


class ProjectMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=ProjectMember.Role.choices,
        required=False,
        help_text="New project role.",
    )
    notes = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Updated notes.",
    )

    def update(self, instance: ProjectMember, validated_data: Dict[str, Any]) -> ProjectMember:
        project_id = self.context.get("project_id")
        company = self.context.get("company")
        actor_membership_id = self.context.get("actor_membership_id")

        if not all([project_id, company, actor_membership_id]):
            raise serializers.ValidationError(
                {"context": "Missing required context."}
            )

        return ProjectMemberService.update_member(
            project_id=project_id,
            company_id=company.id,
            member_id=instance.id,
            role=validated_data.get("role"),
            notes=validated_data.get("notes"),
            actor_membership_id=actor_membership_id,
        )


class ProjectMemberTransferOwnershipSerializer(serializers.Serializer):
    new_owner_membership_id = serializers.IntegerField(
        min_value=1,
        help_text="Membership ID of the new project owner.",
    )

    def save(self, **kwargs) -> Dict[str, Any]:
        project_id = self.context.get("project_id")
        company = self.context.get("company")
        actor_membership_id = self.context.get("actor_membership_id")

        if not all([project_id, company, actor_membership_id]):
            raise serializers.ValidationError(
                {"context": "Missing required context."}
            )

        return ProjectMemberService.transfer_ownership(
            project_id=project_id,
            company_id=company.id,
            new_owner_membership_id=self.validated_data["new_owner_membership_id"],
            actor_membership_id=actor_membership_id,
        )


class ProjectMemberRemoveSerializer(serializers.Serializer):
    def delete(self, instance: ProjectMember) -> Dict[str, Any]:
        project_id = self.context.get("project_id")
        company = self.context.get("company")
        actor_membership_id = self.context.get("actor_membership_id")

        if not all([project_id, company, actor_membership_id]):
            raise serializers.ValidationError(
                {"context": "Missing required context."}
            )

        return ProjectMemberService.remove_member(
            project_id=project_id,
            company_id=company.id,
            member_id=instance.id,
            actor_membership_id=actor_membership_id,
        )