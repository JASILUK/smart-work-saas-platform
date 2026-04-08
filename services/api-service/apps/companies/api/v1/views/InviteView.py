from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.api.base import BaseCompanyAPIView
from apps.companies.api.v1.serializers.serializers import (
    AcceptInviteSerializer,
    BulkInviteSerializer,
    InviteSerializer,
    InviteTokenSerializer,
)
from apps.companies.services.bulk_invite_service import BulkInviteService
from apps.companies.services.company_context_service import CompanyContextService
from apps.companies.services.csv_parser import CSVInviteParser
from apps.companies.services.invite_service import CompanyInviteService
from apps.core.api_response import ApiResponse
from apps.core.mixins import BulkResponseMixin
from apps.users.services.auth_service import AuthService


class InviteEmployeeAPI(BaseCompanyAPIView):

    required_permission = {
        "POST": "tenant.employee.create",
    }

    def post(self, request):

        serializer = InviteSerializer(data=request.data, company=request.company)
        serializer.is_valid(raise_exception=True)

        service = CompanyInviteService()

        service.create_invite(
            company=request.company,
            inviter=request.user,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            department=serializer.validated_data.get("department"),
        )

        return Response(
            {"success": True, "message": "Invitation sent successfully."},
            status=status.HTTP_201_CREATED,
        )


class InviteDetailsAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = InviteTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CompanyInviteService()

        invite, user_exists = service.validate_invite(
            full_token=serializer.validated_data["token"]
        )

        return Response(
            {
                "email": invite.email,
                "company": invite.company.name,
                "invited_by": invite.invited_by.username,
                "requires_registration": not user_exists,
            },
            status=status.HTTP_200_OK,
        )


class AcceptInviteAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CompanyInviteService()

        user, company = service.accept_invite(
            full_token=serializer.validated_data["token"],
            request_user=request.user if request.user.is_authenticated else None,
            password=serializer.validated_data.get("password"),
            username=serializer.validated_data.get("username"),
        )

        if request.user.is_authenticated:

            return Response(
                {
                    "success": True,
                    "message": "Joined successfully",
                    "company_id": company.id,
                }
            )

        auth_service = AuthService()
        payload = auth_service._build_login_payload(user=user)
        strategy = auth_service._get_strategy(
            client_type=request.headers.get("X-Client-Type", "web")
        )
        return strategy.build_response(payload=payload)


class BulkInviteAPI(BaseCompanyAPIView, BulkResponseMixin):

    required_permission = {
        "POST": "tenant.employee.create",
    }

    def post(self, request):
        serializer = BulkInviteSerializer(data=request.data, company=request.company)
        serializer.is_valid(raise_exception=True)

        service = BulkInviteService()

        result = service.process(
            company=request.company,
            inviter=request.user,
            invite_items=serializer.validated_data["invites"],
        )

        return self.build_bulk_response(
            result,
            success_message="All invitations created successfully.",
            partial_message="Bulk invite partially completed.",
            empty_message="No invitations were created.",
        )


class BulkInviteCSVUploadAPI(BaseCompanyAPIView, BulkResponseMixin):

    required_permission = {
        "POST": "tenant.employee.create",
    }

    def post(self, request):

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "CSV file required"}, status=400)

        service = BulkInviteService()

        result = service.process_csv(
            company=request.company, inviter=request.user, file=file
        )

        return self.build_bulk_response(
            result,
            success_message="All CSV invitations created successfully.",
            partial_message="CSV bulk invite partially completed.",
            empty_message="No invitations were created from CSV.",
        )


class CurrentCompanyContextAPI(BaseCompanyAPIView):

    def get(self, request):

        service = CompanyContextService()

        context = service.get_company_context(request)

        return ApiResponse.success(
            data=context,
            message="Company context retrieved successfully",
            status=status.HTTP_200_OK,
        )
