# core/mixins.py
from rest_framework import status
from rest_framework.response import Response


class BulkResponseMixin:

    def build_bulk_response(
        self, result, success_message, partial_message, empty_message
    ):

        created = result.get("created_count", 0)
        failed = result.get("failed_count", 0)

        if created > 0 and failed == 0:
            response_status = status.HTTP_201_CREATED
            message = success_message

        elif created > 0 and failed > 0:
            response_status = status.HTTP_207_MULTI_STATUS
            message = partial_message

        else:
            response_status = status.HTTP_400_BAD_REQUEST
            message = empty_message

        return Response(
            {"success": created > 0, "message": message, "data": result},
            status=response_status,
        )
