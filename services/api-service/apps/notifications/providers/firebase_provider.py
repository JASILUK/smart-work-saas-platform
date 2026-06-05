from firebase_admin import messaging

from integrations.firebase import (
    initialize_firebase,
)

from apps.notifications.models import (
    NotificationDevice,
)


class FirebaseProvider:

    # =====================================================
    # BUILD SAFE DATA PAYLOAD
    # =====================================================

    @staticmethod
    def _build_safe_data(
        *,
        title,
        body,
        data=None,
    ):

        return {

            "title": str(title),

            "body": str(body),

            **{
                str(key): str(value)

                for key, value
                in (data or {}).items()

                if value is not None
            },
        }

    # =====================================================
    # SEND SINGLE PUSH
    # =====================================================

    @staticmethod
    def send_push(
        *,
        token,
        title,
        body,
        data=None,
    ):

        initialize_firebase()

        try:

            safe_data = (
                FirebaseProvider
                ._build_safe_data(
                    title=title,
                    body=body,
                    data=data,
                )
            )

            message = messaging.Message(

                token=token,

                data=safe_data,

                webpush=messaging.WebpushConfig(

                    headers={
                        "Urgency": "high",
                    },
                ),
            )

            response = messaging.send(
                message
            )

            return {

                "success": True,

                "provider_id": response,
            }

        # =================================================
        # TOKEN NO LONGER VALID
        # =================================================

        except messaging.UnregisteredError:

            NotificationDevice.objects.filter(
                token=token,
            ).update(
                is_active=False,
            )

            return {

                "success": False,

                "error": (
                    "Device unregistered."
                ),

                "type": (
                    "UnregisteredError"
                ),
            }

        # =================================================
        # OTHER FIREBASE ERRORS
        # =================================================

        except Exception as exc:

            import traceback

            traceback.print_exc()

            return {

                "success": False,

                "error": repr(exc),

                "type": (
                    type(exc).__name__
                ),
            }

    # =====================================================
    # SEND MULTIPLE PUSHES
    # =====================================================

    @staticmethod
    def send_multicast(
        *,
        tokens,
        title,
        body,
        data=None,
    ):

        initialize_firebase()

        try:

            safe_data = (
                FirebaseProvider
                ._build_safe_data(
                    title=title,
                    body=body,
                    data=data,
                )
            )

            message = (
                messaging.MulticastMessage(

                    tokens=tokens,

                    data=safe_data,

                    webpush=messaging.WebpushConfig(

                        headers={
                            "Urgency": "high",
                        },
                    ),
                )
            )

            response = (
                messaging.send_each_for_multicast(
                    message
                )
            )

            # =============================================
            # DEACTIVATE INVALID TOKENS
            # =============================================

            for index, result in enumerate(
                response.responses
            ):

                if result.success:
                    continue

                if isinstance(
                    result.exception,
                    messaging.UnregisteredError,
                ):

                    NotificationDevice.objects.filter(
                        token=tokens[index],
                    ).update(
                        is_active=False,
                    )

            return {

                "success": True,

                "success_count": (
                    response.success_count
                ),

                "failure_count": (
                    response.failure_count
                ),
            }

        except Exception as exc:

            import traceback

            traceback.print_exc()

            return {

                "success": False,

                "error": repr(exc),

                "type": (
                    type(exc).__name__
                ),
            }