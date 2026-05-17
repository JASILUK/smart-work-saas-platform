from rest_framework.request import Request

from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.companies.api.v1.serializers.DepartmentSerailzer import (

    DepartmentAssignMemberSerializer,

    DepartmentBulkAssignSerializer,

    DepartmentTransferMemberSerializer,
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

from apps.core.api_response import (
    ApiResponse,
)


class DepartmentAssignMemberAPI(
    BaseCompanyAPIView
):

    required_permissions = {
        "POST": "tenant.department.update",
    }

    def post(
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
            DepartmentBulkAssignSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership_ids = (
            serializer.validated_data[
                "membership_ids"
            ]
        )

        memberships = (
            Membership.objects.filter(
                id__in=membership_ids,
                company=request.company,
                is_active=True,
            )
            .select_related("user")
        )

        updated_memberships = (
            DepartmentApplicationService
            .bulk_assign_members(
                department=department,
                memberships=memberships,
            )
        )

        return ApiResponse.success(

            data={

                "department_id": (
                    department.id
                ),

                "membership_ids": [

                    membership.id

                    for membership in updated_memberships
                ],
            },

            message="Members assigned successfully",
        )


class DepartmentRemoveMemberAPI(
    BaseCompanyAPIView
):

    required_permissions = {
        "POST": "tenant.department.update",
    }

    def post(
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
            DepartmentAssignMemberSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership = Membership.objects.get(
            id=serializer.validated_data[
                "membership_id"
            ],
            company=request.company,
            is_active=True,
        )

        DepartmentApplicationService.remove_member(
            department=department,
            membership=membership,
        )

        return ApiResponse.success(
            message="Member removed from department",
        )


class DepartmentTransferMemberAPI(
    BaseCompanyAPIView
):

    required_permissions = {
        "POST": "tenant.department.update",
    }

    def post(
        self,
        request: Request,
        pk: int,
    ):

        from_department = (
            DepartmentSelector.get_by_id(
                pk,
                request.company,
            )
        )

        serializer = (
            DepartmentTransferMemberSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership = Membership.objects.get(
            id=serializer.validated_data[
                "membership_id"
            ],
            company=request.company,
            is_active=True,
        )

        to_department = (
            DepartmentSelector.get_by_id(
                serializer.validated_data[
                    "to_department_id"
                ],
                request.company,
            )
        )

        DepartmentApplicationService.transfer_member(

            membership=membership,

            from_department=from_department,

            to_department=to_department,
        )

        return ApiResponse.success(
            message="Member transferred successfully",
        )