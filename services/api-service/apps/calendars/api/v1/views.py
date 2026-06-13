# apps/calendars/api/v1/views.py

from apps.calendars.services.calendar_account_service import CalendarAccountService
from rest_framework import status

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse




from apps.calendars.api.v1.serializers import (
    CalendarDisconnectSerializer,
    CalendarOAuthCallbackSerializer,
    ConnectedAccountsSerializer,
)



    


# =========================================================
# CONNECT URL
# =========================================================

class CalendarConnectUrlView(
    BaseCompanyAPIView,
):

    def get(
        self,
        request,
    ):

        provider = request.query_params.get(
            "provider"
        )

        if not provider:

            return ApiResponse.error(
                message=(
                    "Provider is required."
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        authorization_url = (

            CalendarAccountService
            .get_connect_url(

                membership=request.membership,

                provider=provider,
            )
        )

        return ApiResponse.success(

            data={
                "provider": provider,
                "authorization_url": (
                    authorization_url
                ),
            }
        )


# =========================================================
# OAUTH CALLBACK
# =========================================================

class CalendarOAuthCallbackView(
    BaseCompanyAPIView,
):

    def post(
        self,
        request,
    ):

        serializer = (
            CalendarOAuthCallbackSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        account = (

            CalendarAccountService.connect_account(
                membership=request.membership,
                provider=serializer.validated_data["provider"],
                code=serializer.validated_data["code"],
                state=serializer.validated_data["state"],
            )
        )

        return ApiResponse.success(

            message=(
                "Calendar connected "
                "successfully."
            ),

            data={

                "provider":
                    account.provider,

                "email":
                    account.email,

                "connected":
                    account.is_connected,
            },
        )


# =========================================================
# DISCONNECT
# =========================================================

class CalendarDisconnectView(
    BaseCompanyAPIView,
):

    def post(
        self,
        request,
    ):

        serializer = (
            CalendarDisconnectSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        CalendarAccountService.disconnect_account(

            membership=request.membership,

            provider=serializer.validated_data[
                "provider"
            ],
        )

        return ApiResponse.success(

            message=(
                "Calendar disconnected "
                "successfully."
            )
        )


# =========================================================
# CONNECTED ACCOUNTS
# =========================================================

class CalendarAccountsView(
    BaseCompanyAPIView,
):

    def get(
        self,
        request,
    ):

        accounts = (

            CalendarAccountService
            .get_connected_accounts(

                membership=request.membership,
            )
        )

        serializer = (
            ConnectedAccountsSerializer(
                instance=accounts,
            )
        )

        return ApiResponse.success(
            message=(
                "Connected calendar accounts retrieved successfully."
            ),
            data=serializer.data,
            status=status.HTTP_200_OK,
        )