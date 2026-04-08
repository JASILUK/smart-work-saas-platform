# companies/views/department_views.py
from apps.companies.api.base import BaseCompanyAPIView
from rest_framework.request import Request

from apps.companies.api.v1.serializers.DepartmentSerailzer import (
    DepartmentCreateUpdateSerializer,
    DepartmentDetailSerializer,
    DepartmentListSerializer,
)
from apps.companies.selectors.DepartmentSelectors import DepartmentSelector
from apps.companies.services.DepartmentService import DepartmentService
from apps.core.api_response import ApiResponse


class DepartmentListAPI(BaseCompanyAPIView):
    """List or create departments."""

    required_permissions = {
        "GET": "tenant.department.view",
        "POST": "tenant.department.create",
    }

    def get(self, request: Request):
        departments = DepartmentSelector.list_by_company(request.company)
        return ApiResponse.success(
            data=DepartmentListSerializer(departments, many=True).data
        )

    def post(self, request: Request):
        serializer = DepartmentCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent = DepartmentSelector.get_by_id_basic(
            serializer.validated_data.get("parent_id"), request.company
        )

        department = DepartmentService.create(
            company=request.company,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description"),
            parent=parent,
        )

        # Fetch with counts for response
        department = DepartmentSelector.get_by_id(department.id, request.company)

        return ApiResponse.success(
            data=DepartmentDetailSerializer(department).data,
            message="Department created",
            status=201,
        )


class DepartmentDetailAPI(BaseCompanyAPIView):
    """Retrieve, update or delete."""

    required_permissions = {
        "GET": "tenant.department.view",
        "PUT": "tenant.department.update",
        "PATCH": "tenant.department.update",
        "DELETE": "tenant.department.delete",
    }

    def get(self, request: Request, pk: int):
        department = DepartmentSelector.get_by_id(pk, request.company)
        return ApiResponse.success(data=DepartmentDetailSerializer(department).data)

    def put(self, request: Request, pk: int):
        return self._update(request, pk, partial=False)

    def patch(self, request: Request, pk: int):
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: int, partial: bool):
        department = DepartmentSelector.get_by_id(pk, request.company)

        serializer = DepartmentCreateUpdateSerializer(
            data=request.data, partial=partial, context={"department_id": pk}
        )
        serializer.is_valid(raise_exception=True)

        # Handle parent
        parent_id = serializer.validated_data.get("parent_id")
        if parent_id is not None:
            parent = DepartmentSelector.get_by_id_basic(parent_id, request.company)
        else:
            parent = None

        updated = DepartmentService.update(
            department=department,
            name=serializer.validated_data.get("name"),
            description=serializer.validated_data.get("description"),
            parent=parent,
        )

        # Re-fetch with counts
        updated = DepartmentSelector.get_by_id(updated.id, request.company)

        return ApiResponse.success(
            data=DepartmentDetailSerializer(updated).data, message="Department updated"
        )

    def delete(self, request: Request, pk: int):
        department = DepartmentSelector.get_by_id(pk, request.company)
        DepartmentService.delete(department)

        return ApiResponse.success(message="Department deleted", status=204)
