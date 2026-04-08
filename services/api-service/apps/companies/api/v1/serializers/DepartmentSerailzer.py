# companies/api/v1/serializers/DepartmentSerializer.py
from typing import List, Optional

from rest_framework import serializers

from apps.companies.models import Department


class DepartmentListSerializer(serializers.ModelSerializer):
    """
    Flat list view - returns scalar parent_id for UI compatibility.
    """

    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, allow_null=True
    )
    children_count = serializers.IntegerField(read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "parent_id",
            "parent_name",
            "children_count",
            "member_count",
            "created_at",
        ]


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """
    Detail view with nested relations.
    """

    parent = DepartmentListSerializer(read_only=True)
    parent_name = serializers.CharField(
        source="parent.name", read_only=True, allow_null=True
    )
    children = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    children_count = serializers.IntegerField(read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "company",
            "parent",  # Nested object for context
            "parent_name",  # Scalar for convenience
            "children",
            "path",
            "children_count",
            "member_count",
            "created_at",
        ]
        read_only_fields = ["company", "created_at"]

    def get_children(self, obj: Department) -> List[dict]:
        """Get immediate children - uses prefetch from selector."""
        # Access prefetched children if available, else query
        children = getattr(obj, "prefetched_children", None)
        if children is None:
            from apps.companies.selectors.DepartmentSelectors import DepartmentSelector

            children = DepartmentSelector.list_children(obj)
        return DepartmentListSerializer(children, many=True).data

    def get_path(self, obj: Department) -> List[dict]:
        """Build breadcrumb path from root to current."""
        path = []
        current = obj
        depth = 0
        max_depth = 10

        while current and depth < max_depth:
            path.append({"id": current.id, "name": current.name})
            current = current.parent
            depth += 1

        return list(reversed(path))


class DepartmentCreateUpdateSerializer(serializers.Serializer):
    """
    Input validation for write operations.
    """

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters")
        return cleaned

    def validate_parent_id(self, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None

        current_id = self.context.get("department_id")
        if current_id and value == current_id:
            raise serializers.ValidationError("Department cannot be its own parent")

        return value
