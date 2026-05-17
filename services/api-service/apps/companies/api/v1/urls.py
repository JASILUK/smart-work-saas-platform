from django.urls import path

from apps.companies.api.v1.views.DepartmentView import DepartmentDetailAPI, DepartmentListAPI
from apps.companies.api.v1.views.EmployeeViews import (
    EmployeeBlockAPI,
    EmployeeDetailAPI,
    EmployeeListAPI,
    EmployeeUnBlockAPI,
)
from apps.companies.api.v1.views.InviteView import (
    AcceptInviteAPI,
    BulkInviteAPI,
    BulkInviteCSVUploadAPI,
    CurrentCompanyContextAPI,
    InviteDetailsAPI,
    InviteEmployeeAPI,
)
from apps.companies.api.v1.views.department_membership_view import DepartmentAssignMemberAPI, DepartmentRemoveMemberAPI, DepartmentTransferMemberAPI

urlpatterns = [
    path("invite/users/", InviteEmployeeAPI.as_view(), name="invite-employee"),
    path("invite/bulk/users/", BulkInviteAPI.as_view(), name="bulk-invite-users"),
    path(
        "invite/bulk_in_csv/users/",
        BulkInviteCSVUploadAPI.as_view(),
        name="bulk-in-csv-invite-users",
    ),
    path("invite/detailes/", InviteDetailsAPI.as_view(), name="invite-detailes-api"),
    path("invite/accept/", AcceptInviteAPI.as_view(), name="accept-invite-api"),
    path(
        "context/", CurrentCompanyContextAPI.as_view(), name="current-company-context"
    ),
    path("employee/", EmployeeListAPI.as_view(), name="emplyee-list-api"),
    path(
        "employee/<int:pk>/", EmployeeDetailAPI.as_view(), name="emplyee-detailed-api"
    ),
    path(
        "employee/<int:pk>/block/", EmployeeBlockAPI.as_view(), name="emplyee-block-api"
    ),
    path(
        "employee/<int:pk>/unblock/",
        EmployeeUnBlockAPI.as_view(),
        name="emplyee-unblock-api",
    ),
       path(
        "departments/",
        DepartmentListAPI.as_view(),
        name="department-list",
    ),

    path(
        "departments/<int:pk>/",
        DepartmentDetailAPI.as_view(),
        name="department-detail",
    ),

    # =====================================================
    # MEMBERSHIP MANAGEMENT
    # =====================================================

    path(
        "departments/<int:pk>/assign-member/",
        DepartmentAssignMemberAPI.as_view(),
        name="department-assign-member",
    ),

    path(
        "departments/<int:pk>/remove-member/",
        DepartmentRemoveMemberAPI.as_view(),
        name="department-remove-member",
    ),

    path(
        "departments/<int:pk>/transfer-member/",
        DepartmentTransferMemberAPI.as_view(),
        name="department-transfer-member",
    ),
]
