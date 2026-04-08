# users/services/auth_strategies.py

from django.conf import settings
from rest_framework.response import Response

from apps.users.models import User


class MobileStrategy:
    def build_response(self, payload):

        return Response(
            {
                "success": True,
                "access": payload["tokens"]["access"],
                "refresh": payload["tokens"]["refresh"],
                "user": payload["user"],
            }
        )

    def issue_logout_response(self) -> Response:
        """Mobile handles its own storage, so we just say success."""
        return Response({"success": True, "message": "Successfully logged out."})


class WebStrategy:

    def build_response(self, payload) -> Response:

        response = Response({"success": True, "user": payload["user"]})

        response.set_cookie(
            key="access_token",
            value=payload["tokens"]["access"],
            max_age=15 * 60,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
        )

        response.set_cookie(
            key="refresh_token",
            value=payload["tokens"]["refresh"],
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
        )

        return response

    def issue_logout_response(self) -> Response:
        """Web needs Django to physically delete the secure cookies."""
        response = Response({"success": True, "message": "Successfully logged out."})

        # This tells the browser: "Destroy these cookies immediately!"
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
