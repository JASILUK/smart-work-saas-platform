from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.selectors import get_active_plans

from .serializers import PlanSerializer


class PlanListAPI(APIView):

    permission_classes = []

    def get(self, request):

        plans = get_active_plans()

        serializer = PlanSerializer(plans, many=True)

        return Response({"success": True, "plans": serializer.data})
