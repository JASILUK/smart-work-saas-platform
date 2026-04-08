from django.urls import path

from apps.billing.api.v1.views import PlanListAPI

urlpatterns = [path("plans/", PlanListAPI.as_view(), name="plan-view")]
