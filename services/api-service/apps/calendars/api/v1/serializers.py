# apps/calendars/api/v1/serializers.py

from apps.calendars.models.calendar_account import CalendarAccount
from rest_framework import serializers


# =========================================================
# CALENDAR ACCOUNT
# =========================================================

class CalendarAccountSerializer(
    serializers.Serializer
):

    connected = serializers.BooleanField()

    email = serializers.EmailField(
        allow_null=True,
    )


# =========================================================
# CONNECTED ACCOUNTS RESPONSE
# =========================================================

class ConnectedAccountsSerializer(
    serializers.Serializer
):

    google = CalendarAccountSerializer()

    outlook = CalendarAccountSerializer()







# =========================================================
# CONNECT URL RESPONSE
# =========================================================

class CalendarConnectUrlSerializer(
    serializers.Serializer
):

    provider = serializers.CharField()

    authorization_url = serializers.URLField()


# =========================================================
# CALLBACK REQUEST
# =========================================================

class CalendarOAuthCallbackSerializer(
    serializers.Serializer
):

    provider = serializers.ChoiceField(
        choices=CalendarAccount.Provider.choices,
    )

    code = serializers.CharField()

    state = serializers.CharField()


# =========================================================
# DISCONNECT REQUEST
# =========================================================

class CalendarDisconnectSerializer(
    serializers.Serializer
):

    provider = serializers.ChoiceField(
        choices=CalendarAccount.Provider.choices,
    )


# =========================================================
# ACCOUNT
# =========================================================

class CalendarAccountSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = CalendarAccount

        fields = [

            "id",

            "provider",

            "email",

            "is_connected",

            "expires_at",

            "created_at",

            "updated_at",
        ]

        read_only_fields = fields


# =========================================================
# CONNECTED PROVIDERS
# =========================================================

class ConnectedCalendarAccountsSerializer(
    serializers.Serializer
):

    google = serializers.DictField()

    outlook = serializers.DictField()


# =========================================================
# CONNECTION STATUS
# =========================================================

class CalendarConnectionStatusSerializer(
    serializers.Serializer
):

    provider = serializers.CharField()

    connected = serializers.BooleanField()

    email = serializers.EmailField(
        allow_null=True,
        required=False,
    )


# =========================================================
# SUCCESS RESPONSE
# =========================================================

class CalendarConnectionResponseSerializer(
    serializers.Serializer
):

    account = CalendarAccountSerializer()

    message = serializers.CharField()