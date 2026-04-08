from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core_platform.permissions import PlatformPermission


class BasePlatformAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
        PlatformPermission,
    ]
