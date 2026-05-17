import logging

from celery import shared_task

from apps.notifications.models import (
    Notification,
    NotificationDevice,
)

from apps.notifications.providers.firebase_provider import (
    FirebaseProvider,
)

logger = logging.getLogger(__name__)

# ========================================================
# PERMANENT TOKEN ERRORS
# ========================================================

PERMANENT_TOKEN_ERRORS = [

    "notregistered",

    "not registered",

    "device unregistered",

    "invalid registration",

    "invalidregistration",

    "requested entity was not found",

    "registration-token-not-registered",

    "unregistered",
]


# ========================================================
# CUSTOM EXCEPTION
# ========================================================

class TemporaryPushFailure(Exception):
    pass


# ========================================================
# TASK
# ========================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_push_notification_task(
    self,
    *,
    device_id,
    notification_id,
):

    try:

        # =================================================
        # DEVICE
        # =================================================

        device = (
            NotificationDevice.objects
            .filter(
                id=device_id,
                is_active=True,
            )
            .first()
        )

        if not device:

            logger.warning(
                "Notification device not found: %s",
                device_id,
            )

            return

        # =================================================
        # NOTIFICATION
        # =================================================

        notification = (
            Notification.objects
            .filter(
                id=notification_id,
            )
            .first()
        )

        if not notification:

            logger.warning(
                "Notification not found: %s",
                notification_id,
            )

            return

        # =================================================
        # FIREBASE SAFE DATA
        # =================================================

        raw_data = {

            "notification_id": str(
                notification.id
            ),

            "type": str(
                notification.type
            ),

            **(
                notification.data or {}
            ),
        }

        safe_data = {

            str(key): str(value)

            for key, value
            in raw_data.items()

            if value is not None
        }

        # =================================================
        # SEND PUSH
        # =================================================

        result = FirebaseProvider.send_push(

            token=device.token,

            title=notification.title,

            body=notification.body,

            data=safe_data,
        )

        logger.info(
            "Push result for device %s: %s",
            device.id,
            result,
        )

        # =================================================
        # SUCCESS
        # =================================================

        if result.get("success"):

            return

        # =================================================
        # FAILURE
        # =================================================

        error_message = str(
            result.get("error", "")
        ).strip().lower()

        logger.error(
            "Push failed for device %s: %s",
            device.id,
            error_message,
        )

        # =================================================
        # PERMANENT TOKEN FAILURE
        # =================================================

        if any(

            error in error_message

            for error
            in PERMANENT_TOKEN_ERRORS
        ):

            device.is_active = False

            device.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

            logger.warning(
                "Disabled invalid push token for device %s",
                device.id,
            )

            return

        # =================================================
        # TEMPORARY FAILURE
        # =================================================

        raise TemporaryPushFailure(
            result.get("error")
        )

    # =====================================================
    # RETRYABLE FAILURE
    # =====================================================

    except TemporaryPushFailure as exc:

        logger.exception(
            "Temporary push notification failure"
        )

        raise self.retry(exc=exc)

    # =====================================================
    # UNEXPECTED FAILURE
    # =====================================================

    except Exception as exc:

        logger.exception(
            "Unexpected push notification task failure"
        )

        raise self.retry(exc=exc)