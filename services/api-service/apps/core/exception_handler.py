import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):


    response = exception_handler(exc, context)
    if response is not None:
        return response

    # 2. Handle our specific Business Logic errors
    if isinstance(exc, ApplicationError):
        return Response(
            {
                "code": exc.code,
                "message": exc.message,
            },
            status=exc.status_code,
        )

    # 3. Log the massive, unexpected crash
    logger.exception("Unhandled exception caught by global handler", exc_info=exc)

    # 4. If on local laptop, crash loudly so we can fix it
    if settings.DEBUG:
        raise exc

    # 5. If in production, fail safely with JSON
    return Response(
        {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Something went wrong. Please try again later.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
