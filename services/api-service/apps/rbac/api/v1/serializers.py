from encodings.punycode import T

from rest_framework import serializers

from apps.rbac.models import Permission, Role


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description", "category", "scope"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        required=False,
        write_only=True,
        source="permissions",
    )

    class Meta:
        model = Role
        fields = ["id", "name", "is_system_role", "permissions", "permission_ids"]
        read_only_fields = ["is_system_role"]
