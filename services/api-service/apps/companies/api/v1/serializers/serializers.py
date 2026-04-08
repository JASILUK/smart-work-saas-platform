# companies/api/v1/serializers.py

from rest_framework import serializers

from apps.companies.models import Department, Membership
from apps.rbac.models import Role


class BaseInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.none())
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.none(), required=False, allow_null=True
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields["role"].queryset = Role.objects.filter(company=company)
            self.fields["department"].queryset = Department.objects.filter(
                company=company
            )


class InviteSerializer(BaseInviteSerializer):
    pass


class BulkInviteItemSerializer(BaseInviteSerializer):
    pass


class BulkInviteSerializer(serializers.Serializer):
    invites = BulkInviteItemSerializer(many=True)

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        if company:
            self.fields["invites"].child = BulkInviteItemSerializer(company=company)


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, required=False)
    username = serializers.CharField(required=False)


class InviteTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class EmployeeSerializer(serializers.ModelSerializer):

    user_email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user_email",
            "username",
            "role",
            "role_name",
            "department",
            "department_name",
            "is_active",
            "job_title",
        ]


class EmployeeUpdateSerializer(serializers.Serializer):

    role_id = serializers.IntegerField(required=False)
    department_id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    title = serializers.CharField(required=False)

    def validate(self, data):

        if not data:
            raise serializers.ValidationError("No fields provided for update.")

        return data
