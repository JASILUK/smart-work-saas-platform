"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/v1/", include("apps.users.api.v1.urls")),
    path("api/billing/v1/", include("apps.billing.api.v1.urls")),
    path("api/company/v1/", include("apps.companies.api.v1.urls")),
    path("api/rbac/v1/", include("apps.rbac.api.v1.urls")),
    path("api/platform/v1/", include("apps.rbac.api.v1.urls")),
    path("api/chat/v1/",include("apps.chat.api.v1.urls")),
    path("api/notification/v1/",include("apps.notifications.api.v1.urls")),
]
