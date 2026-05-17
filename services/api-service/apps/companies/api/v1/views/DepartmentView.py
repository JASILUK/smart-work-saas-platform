# apps/companies/api/v1/views/department_views.py

from rest_framework.request import Request

from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.companies.api.v1.serializers.DepartmentSerailzer import (
    DepartmentCreateUpdateSerializer,
    DepartmentDetailSerializer,
    DepartmentListSerializer,
)

from apps.companies.models import (
    Membership,
)

from apps.companies.selectors.DepartmentSelectors import (
    DepartmentSelector,
)

from apps.companies.services.department_application_service import (
    DepartmentApplicationService,
)

from apps.companies.services.DepartmentService import (
    DepartmentService,
)

from apps.core.api_response import (
    ApiResponse,
)


class DepartmentListAPI(
    BaseCompanyAPIView
):

    required_permissions = {

        "GET": "tenant.department.view",

        "POST": "tenant.department.create",
    }

    # =====================================================
    # LIST DEPARTMENTS
    # =====================================================

    def get(
        self,
        request: Request,
    ):

        departments = (
            DepartmentSelector.list_by_company(
                request.company,
            )
        )

        serializer = (
            DepartmentListSerializer(
                departments,
                many=True,
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )

    # =====================================================
    # CREATE DEPARTMENT
    # =====================================================

    def post(
        self,
        request: Request,
    ):

        serializer = (
            DepartmentCreateUpdateSerializer(
                data=request.data,
                context={
                    "request": request,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        validated_data = (
            serializer.validated_data
        )

        # =================================================
        # PARENT
        # =================================================

        parent = None

        parent_id = validated_data.get(
            "parent_id"
        )

        if parent_id is not None:

            parent = (
                DepartmentSelector.get_by_id_basic(
                    parent_id,
                    request.company,
                )
            )

        # =================================================
        # HEAD
        # =================================================

        head = None

        head_membership_id = (
            validated_data.get(
                "head_membership_id"
            )
        )

        if head_membership_id is not None:

            head = (
                Membership.objects.get(
                    id=head_membership_id,
                    company=request.company,
                    is_active=True,
                )
            )

        # =================================================
        # CREATE WORKFLOW
        # =================================================

        department = (
            DepartmentApplicationService
            .create_department(

                company=request.company,

                created_by=request.user,

                name=validated_data.get(
                    "name"
                ),

                description=validated_data.get(
                    "description"
                ),

                parent=parent,

                head=head,
            )
        )

        department = (
            DepartmentSelector.get_by_id(
                department.id,
                request.company,
            )
        )

        return ApiResponse.success(

            data=DepartmentDetailSerializer(
                department
            ).data,

            message="Department created",

            status=201,
        )


class DepartmentDetailAPI(
    BaseCompanyAPIView
):

    required_permissions = {

        "GET": "tenant.department.view",

        "PUT": "tenant.department.update",

        "PATCH": "tenant.department.update",

        "DELETE": "tenant.department.delete",
    }

    # =====================================================
    # GET DEPARTMENT
    # =====================================================

    def get(
        self,
        request: Request,
        pk: int,
    ):

        department = (
            DepartmentSelector.get_by_id(
                pk,
                request.company,
            )
        )

        serializer = (
            DepartmentDetailSerializer(
                department
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )

    # =====================================================
    # PUT
    # =====================================================

    def put(
        self,
        request: Request,
        pk: int,
    ):

        return self._update(
            request=request,
            pk=pk,
            partial=False,
        )

    # =====================================================
    # PATCH
    # =====================================================

    def patch(
        self,
        request: Request,
        pk: int,
    ):

        return self._update(
            request=request,
            pk=pk,
            partial=True,
        )

    # =====================================================
    # UPDATE DEPARTMENT
    # =====================================================

    def _update(
        self,
        *,
        request: Request,
        pk: int,
        partial: bool,
    ):

        department = (
            DepartmentSelector.get_by_id(
                pk,
                request.company,
            )
        )

        serializer = (
            DepartmentCreateUpdateSerializer(

                data=request.data,

                partial=partial,

                context={

                    "request": request,

                    "department_id": pk,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        validated_data = (
            serializer.validated_data
        )

        # =================================================
        # PARENT
        # =================================================

        parent = DepartmentService.UNSET

        if "parent_id" in validated_data:

            parent_id = validated_data.get(
                "parent_id"
            )

            if parent_id is None:

                parent = None

            else:

                parent = (
                    DepartmentSelector.get_by_id_basic(
                        parent_id,
                        request.company,
                    )
                )

        # =================================================
        # HEAD
        # =================================================

        head = DepartmentService.UNSET

        if (
            "head_membership_id"
            in validated_data
        ):

            head_membership_id = (
                validated_data.get(
                    "head_membership_id"
                )
            )

            if head_membership_id is None:

                head = None

            else:

                head = (
                    Membership.objects.get(
                        id=head_membership_id,
                        company=request.company,
                        is_active=True,
                    )
                )

        # =================================================
        # UPDATE WORKFLOW
        # =================================================

        updated_department = (
            DepartmentApplicationService
            .update_department(

                department=department,

                name=validated_data.get(
                    "name",
                    DepartmentService.UNSET,
                ),

                description=validated_data.get(
                    "description",
                    DepartmentService.UNSET,
                ),

                parent=parent,

                head=head,
            )
        )

        updated_department = (
            DepartmentSelector.get_by_id(
                updated_department.id,
                request.company,
            )
        )

        return ApiResponse.success(

            data=DepartmentDetailSerializer(
                updated_department
            ).data,

            message="Department updated",
        )

    # =====================================================
    # DELETE DEPARTMENT
    # =====================================================

    def delete(
        self,
        request: Request,
        pk: int,
    ):

        department = (
            DepartmentSelector.get_by_id(
                pk,
                request.company,
            )
        )

        DepartmentApplicationService.delete_department(
            department=department,
        )

        return ApiResponse.success(

            message="Department deleted",

            status=204,
        )