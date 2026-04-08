from rest_framework.response import Response


class ApiResponse:

    @staticmethod
    def success(data=None, message="Success", status=200):
        return Response(
            {
                "success": True,
                "message": message,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def error(data=None, message="Error", status=400):
        return Response(
            {
                "success": False,
                "message": message,
                "data": data,
            },
            status=status,
        )
