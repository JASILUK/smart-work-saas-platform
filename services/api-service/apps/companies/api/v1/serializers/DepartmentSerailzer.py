from typing import List

from rest_framework import serializers

from apps.companies.models import (
    Department,
    Membership,
)


class DepartmentListSerializer(
    serializers.ModelSerializer
):

    parent_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
    )

    head_id = serializers.IntegerField(
        source="head.id",
        read_only=True,
        allow_null=True,
    )

    head_name = serializers.SerializerMethodField()

    children_count = serializers.IntegerField(
        read_only=True,
    )

    member_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:

        model = Department

        fields = [

            "id",

            "name",

            "description",

            "parent_id",

            "parent_name",

            "head_id",

            "head_name",

            "children_count",

            "member_count",

            "created_at",
        ]

    def get_head_name(
        self,
        obj,
    ):

        if not obj.head:
            return None

        return (
            obj.head.user.get_full_name()
            or obj.head.user.username
        )


class DepartmentDetailSerializer(
    serializers.ModelSerializer
):

    parent = DepartmentListSerializer(
        read_only=True,
    )

    children = serializers.SerializerMethodField()

    path = serializers.SerializerMethodField()

    head = serializers.SerializerMethodField()

    members = serializers.SerializerMethodField()

    children_count = serializers.IntegerField(
        read_only=True,
    )

    member_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:

        model = Department

        fields = [

            "id",

            "name",

            "description",

            "company",

            "parent",

            "children",

            "path",

            "head",

            "members",

            "children_count",

            "member_count",

            "created_at",
        ]

        read_only_fields = [

            "company",

            "created_at",
        ]

    # =====================================================
    # CHILDREN
    # =====================================================

    def get_children(
        self,
        obj,
    ):

        children = getattr(
            obj,
            "prefetched_children",
            None,
        )

        if children is None:

            from apps.companies.selectors.DepartmentSelectors import (
                DepartmentSelector,
            )

            children = (
                DepartmentSelector.list_children(
                    obj
                )
            )

        return (
            DepartmentListSerializer(
                children,
                many=True,
            ).data
        )

    # =====================================================
    # PATH
    # =====================================================

    def get_path(
        self,
        obj,
    ):

        path = []

        current = obj

        depth = 0

        max_depth = 20

        while current and depth < max_depth:

            path.append({

                "id": current.id,

                "name": current.name,
            })

            current = current.parent

            depth += 1

        return list(
            reversed(path)
        )

    # =====================================================
    # HEAD
    # =====================================================

    def get_head(
        self,
        obj,
    ):

        if not obj.head:
            return None

        membership = obj.head

        return {

            "id": membership.id,

            "user_id": membership.user_id,

            "name": (
                membership.user.get_full_name()
                or membership.user.username
            ),

            "email": (
                membership.work_space_email
            ),

            "job_title": (
                membership.job_title
            ),
        }

    # =====================================================
    # MEMBERS
    # =====================================================

    def get_members(
        self,
        obj,
    ):

        memberships = (
            Membership.objects
            .filter(
                department=obj,
                is_active=True,
            )
            .select_related(
                "user",
            )
            .order_by(
                "user__username",
            )
        )

        return [

            {

                "membership_id": membership.id,

                "user_id": membership.user_id,

                "name": (
                    membership.user.get_full_name()
                    or membership.user.username
                ),

                "email": (
                    membership.work_space_email
                ),

                "job_title": (
                    membership.job_title
                ),

                "is_head": (
                    obj.head_id == membership.id
                ),
            }

            for membership in memberships
        ]


class DepartmentCreateUpdateSerializer(
    serializers.Serializer
):

    name = serializers.CharField(
        max_length=100,
        required=False,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    parent_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    head_membership_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    def validate_name(
        self,
        value,
    ):

        cleaned = (
            value or ""
        ).strip()

        if len(cleaned) < 2:

            raise serializers.ValidationError(
                "Department name must be at least 2 characters"
            )

        return cleaned

    def validate_head_membership_id(
        self,
        value,
    ):

        if value is None:
            return None

        request = self.context.get(
            "request"
        )

        company = getattr(
            request,
            "company",
            None,
        )

        exists = (
            Membership.objects.filter(
                id=value,
                company=company,
                is_active=True,
            )
            .exists()
        )

        if not exists:

            raise serializers.ValidationError(
                "Invalid department head"
            )

        return value

    def validate_parent_id(
        self,
        value,
    ):

        if value is None:
            return None

        current_department_id = (
            self.context.get(
                "department_id"
            )
        )

        if (
            current_department_id
            and
            value == current_department_id
        ):

            raise serializers.ValidationError(
                "Department cannot be its own parent"
            )

        return value
    


from rest_framework import serializers


class DepartmentAssignMemberSerializer(
    serializers.Serializer
):

    membership_id = serializers.IntegerField()


class DepartmentBulkAssignSerializer(
    serializers.Serializer
):

    membership_ids = serializers.ListField(

        child=serializers.IntegerField(),

        allow_empty=False,
    )


class DepartmentTransferMemberSerializer(
    serializers.Serializer
):

    membership_id = serializers.IntegerField()

    to_department_id = serializers.IntegerField()