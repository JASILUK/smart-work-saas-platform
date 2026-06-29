# =====================================================
# VIEWS
# =====================================================
# apps/leave/views.py
# =====================================================

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import StandardLimitOffsetPagination
from apps.attendance.models.leave import LeaveType, LeaveBalance, LeaveRequest
from apps.attendance.selectors.leave_selector import (
    LeaveTypeSelector,
    LeaveBalanceSelector,
    LeaveRequestSelector,
)
from apps.attendance.services.leave_service import (
    LeaveTypeService,
    LeaveBalanceService,
    LeaveRequestService,
)
from apps.attendance.api.v1.serializers.leave_serializers import (
    LeaveTypeListSerializer,
    LeaveTypeDetailSerializer,
    LeaveTypeCreateUpdateSerializer,
    LeaveBalanceListSerializer,
    LeaveBalanceDetailSerializer,
    LeaveBalanceAdjustmentSerializer,
    LeaveBalanceAllocationSerializer,
    LeaveRequestListSerializer,
    LeaveRequestDetailSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestApproveSerializer,
    LeaveRequestRejectSerializer,
    LeaveRequestCancelSerializer,
    LeaveRequestStatisticsSerializer,
    LeaveRequestPaginatedResponseSerializer,
)


class MyLeaveBalancesAPI(BaseCompanyAPIView):
    """
    GET /leave/me/leave-balances/
    Returns leave balances for the logged-in employee.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        membership = request.membership
        leave_year = request.query_params.get("year")

        year = int(leave_year) if leave_year else timezone.now().year

        balances = LeaveBalanceSelector.get_employee_balances(
            membership=membership,
            leave_year=year,
        )

        serializer = LeaveBalanceListSerializer(balances, many=True)
        return ApiResponse.success(data=serializer.data)


class MyLeaveRequestsAPI(BaseCompanyAPIView):
    """
    GET /leave/me/leave-requests/
    POST /leave/me/leave-requests/
    """
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.view"}
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        membership = request.membership

        status_filter = request.query_params.get("status")
        leave_type_id = request.query_params.get("leave_type")
        year = request.query_params.get("year")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        ordering = request.query_params.get("ordering", "-created_at")

        parsed_date_from = (
            timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            if date_from else None
        )
        parsed_date_to = (
            timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            if date_to else None
        )
        parsed_year = int(year) if year else None
        parsed_leave_type_id = int(leave_type_id) if leave_type_id else None

        requests = LeaveRequestSelector.get_my_requests(
            membership=membership,
            status=status_filter,
            leave_type_id=parsed_leave_type_id,
            year=parsed_year,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
        )

        if ordering:
            requests = requests.order_by(ordering)

        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(requests, request)
        serializer = LeaveRequestListSerializer(page, many=True)

        paginated_response = paginator.get_paginated_response(serializer.data)
        return ApiResponse.success(data=paginated_response.data)

    def post(self, request, *args, **kwargs):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        leave_request = LeaveRequestService.create_request(
            company=request.company,
            membership=request.membership,
            leave_type_id=data["leave_type_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            is_half_day=data.get("is_half_day", False),
            half_day_session=data.get("half_day_session", ""),
            reason=data["reason"],
            attachment=request.FILES.get("attachment"),
        )

        response_serializer = LeaveRequestDetailSerializer(leave_request)
        return ApiResponse.success(
            data=response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class MyLeaveRequestDetailAPI(BaseCompanyAPIView):
    """
    GET /leave/me/leave-requests/{id}/
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_my_request_detail(
            request_id=request_id,
            membership=request.membership,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestDetailSerializer(leave_request)
        return ApiResponse.success(data=serializer.data)


class MyLeaveRequestCancelAPI(BaseCompanyAPIView):
    """
    POST /leave/me/leave-requests/{id}/cancel/
    """
    required_permissions = {"POST": "tenant.attendance.view"}

    def post(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_my_request_detail(
            request_id=request_id,
            membership=request.membership,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cancelled = LeaveRequestService.cancel_request(
            leave_request=leave_request,
            canceller=request.membership,
        )

        response_serializer = LeaveRequestDetailSerializer(cancelled)
        return ApiResponse.success(data=response_serializer.data)


class LeaveRequestListAPI(BaseCompanyAPIView):
    """
    GET /leave/leave-requests/
    HR view for all company leave requests with statistics.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        company = request.company

        employee = request.query_params.get("employee")
        department = request.query_params.get("department")
        leave_type = request.query_params.get("leave_type")
        status_filter = request.query_params.get("status")
        year = request.query_params.get("year")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        ordering = request.query_params.get("ordering", "-created_at")

        parsed_date_from = (
            timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            if date_from else None
        )
        parsed_date_to = (
            timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            if date_to else None
        )
        parsed_year = int(year) if year else None
        parsed_employee = int(employee) if employee else None
        parsed_department = int(department) if department else None
        parsed_leave_type = int(leave_type) if leave_type else None

        requests = LeaveRequestSelector.get_company_requests(
            company=company,
            status=status_filter,
            leave_type_id=parsed_leave_type,
            membership_id=parsed_employee,
            department_id=parsed_department,
            year=parsed_year,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
        )

        if ordering:
            requests = requests.order_by(ordering)

        statistics = LeaveRequestSelector.get_statistics(company=company)

        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(requests, request)
        results_serializer = LeaveRequestListSerializer(page, many=True)

        paginated_data = paginator.get_paginated_response(results_serializer.data).data

        response_data = {
            "statistics": statistics,
            **paginated_data,
        }

        return ApiResponse.success(data=response_data)


class LeaveRequestDetailAPI(BaseCompanyAPIView):
    """
    GET /leave/leave-requests/{id}/
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_request_detail_for_hr(
            request_id=request_id,
            company=request.company,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestDetailSerializer(leave_request)
        return ApiResponse.success(data=serializer.data)


class LeaveRequestApproveAPI(BaseCompanyAPIView):
    """
    POST /leave/leave-requests/{id}/approve/
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_by_id(
            request_id=request_id,
            company=request.company,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approved = LeaveRequestService.approve_request(
            leave_request=leave_request,
            approver=request.membership,
        )

        response_serializer = LeaveRequestDetailSerializer(approved)
        return ApiResponse.success(data=response_serializer.data)


class LeaveRequestRejectAPI(BaseCompanyAPIView):
    """
    POST /leave/leave-requests/{id}/reject/
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_by_id(
            request_id=request_id,
            company=request.company,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rejected = LeaveRequestService.reject_request(
            leave_request=leave_request,
            rejector=request.membership,
            rejection_reason=serializer.validated_data["rejection_reason"],
        )

        response_serializer = LeaveRequestDetailSerializer(rejected)
        return ApiResponse.success(data=response_serializer.data)


class LeaveRequestCancelHRAPI(BaseCompanyAPIView):
    """
    POST /leave/leave-requests/{id}/cancel/
    HR cancel endpoint.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, request_id, *args, **kwargs):
        leave_request = LeaveRequestSelector.get_by_id(
            request_id=request_id,
            company=request.company,
        )
        if not leave_request:
            return ApiResponse.error("Leave request not found.")

        serializer = LeaveRequestCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cancelled = LeaveRequestService.hr_cancel_request(
            leave_request=leave_request,
            canceller=request.membership,
        )

        response_serializer = LeaveRequestDetailSerializer(cancelled)
        return ApiResponse.success(data=response_serializer.data)


class EmployeeLeaveBalancesAPI(BaseCompanyAPIView):
    """
    GET /leave/employees/{membership_id}/leave-balances/
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, membership_id, *args, **kwargs):
        from apps.companies.models import Membership

        try:
            membership = Membership.objects.get(
                id=membership_id,
                company=request.company,
            )
        except Membership.DoesNotExist:
            return ApiResponse.error("Employee not found.")

        leave_year = request.query_params.get("year")
        year = int(leave_year) if leave_year else timezone.now().year

        balances = LeaveBalanceSelector.get_employee_balances(
            membership=membership,
            leave_year=year,
        )

        serializer = LeaveBalanceListSerializer(balances, many=True)
        return ApiResponse.success(data=serializer.data)


class EmployeeLeaveRequestsAPI(BaseCompanyAPIView):
    """
    GET /leave/employees/{membership_id}/leave-requests/
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, membership_id, *args, **kwargs):
        from apps.companies.models import Membership

        try:
            membership = Membership.objects.get(
                id=membership_id,
                company=request.company,
            )
        except Membership.DoesNotExist:
            return ApiResponse.error("Employee not found.")

        status_filter = request.query_params.get("status")
        leave_type_id = request.query_params.get("leave_type")
        year = request.query_params.get("year")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        parsed_date_from = (
            timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            if date_from else None
        )
        parsed_date_to = (
            timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            if date_to else None
        )
        parsed_year = int(year) if year else None
        parsed_leave_type_id = int(leave_type_id) if leave_type_id else None

        requests = LeaveRequestSelector.get_my_requests(
            membership=membership,
            status=status_filter,
            leave_type_id=parsed_leave_type_id,
            year=parsed_year,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
        )

        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(requests, request)
        serializer = LeaveRequestListSerializer(page, many=True)

        paginated_response = paginator.get_paginated_response(serializer.data)
        return ApiResponse.success(data=paginated_response.data)


class LeaveTypeListCreateAPI(BaseCompanyAPIView):
    """
    GET /leave/leave-types/
    POST /leave/leave-types/
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request, *args, **kwargs):
        active_only = request.query_params.get("active_only", "false").lower() == "true"

        if active_only:
            leave_types = LeaveTypeSelector.list_active_by_company(company=request.company)
        else:
            leave_types = LeaveTypeSelector.list_by_company(company=request.company)

        serializer = LeaveTypeListSerializer(leave_types, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = LeaveTypeCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leave_type = LeaveTypeService.create(
            company=request.company,
            **serializer.validated_data,
        )

        response_serializer = LeaveTypeDetailSerializer(leave_type)
        return ApiResponse.success(
            data=response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class LeaveTypeDetailUpdateDeleteAPI(BaseCompanyAPIView):
    """
    GET /leave/leave-types/{id}/
    PUT /leave/leave-types/{id}/
    DELETE /leave/leave-types/{id}/
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
        "PUT": "tenant.attendance.manage",
        "DELETE": "tenant.attendance.manage",
    }

    def get(self, request, leave_type_id, *args, **kwargs):
        leave_type = LeaveTypeSelector.get_by_id(
            leave_type_id=leave_type_id,
            company=request.company,
        )
        if not leave_type:
            return ApiResponse.error("Leave type not found.")

        serializer = LeaveTypeDetailSerializer(leave_type)
        return ApiResponse.success(data=serializer.data)

    def put(self, request, leave_type_id, *args, **kwargs):
        leave_type = LeaveTypeSelector.get_by_id(
            leave_type_id=leave_type_id,
            company=request.company,
        )
        if not leave_type:
            return ApiResponse.error("Leave type not found.")

        serializer = LeaveTypeCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = LeaveTypeService.update(
            leave_type=leave_type,
            **serializer.validated_data,
        )

        response_serializer = LeaveTypeDetailSerializer(updated)
        return ApiResponse.success(data=response_serializer.data)

    def delete(self, request, leave_type_id, *args, **kwargs):
        leave_type = LeaveTypeSelector.get_by_id(
            leave_type_id=leave_type_id,
            company=request.company,
        )
        if not leave_type:
            return ApiResponse.error("Leave type not found.")

        LeaveTypeService.deactivate(leave_type=leave_type)
        return ApiResponse.success(message="Leave type deactivated successfully.")


class LeaveBalanceListAPI(BaseCompanyAPIView):
    """
    GET /leave/leave-balances/
    HR list view for company leave balances.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        leave_year = request.query_params.get("year")
        membership_id = request.query_params.get("membership")
        leave_type_id = request.query_params.get("leave_type")

        parsed_year = int(leave_year) if leave_year else timezone.now().year
        parsed_membership = int(membership_id) if membership_id else None
        parsed_leave_type = int(leave_type_id) if leave_type_id else None

        balances = LeaveBalanceSelector.list_company_balances(
            company=request.company,
            leave_year=parsed_year,
            membership_id=parsed_membership,
            leave_type_id=parsed_leave_type,
        )

        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(balances, request)
        serializer = LeaveBalanceListSerializer(page, many=True)

        paginated_response = paginator.get_paginated_response(serializer.data)
        return ApiResponse.success(data=paginated_response.data)


class LeaveBalanceAdjustAPI(BaseCompanyAPIView):
    """
    POST /leave/leave-balances/{id}/adjust/
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, balance_id, *args, **kwargs):
        balance = LeaveBalanceSelector.get_by_id(
            balance_id=balance_id,
            company=request.company,
        )
        if not balance:
            return ApiResponse.error("Leave balance not found.")

        serializer = LeaveBalanceAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjusted = LeaveBalanceService.manual_adjustment(
            balance=balance,
            adjustment_days=serializer.validated_data["adjustment_days"],
            reason=serializer.validated_data.get("reason", ""),
        )

        response_serializer = LeaveBalanceDetailSerializer(adjusted)
        return ApiResponse.success(data=response_serializer.data)


class LeaveBalanceAllocateAPI(BaseCompanyAPIView):
    """
    POST /leave/leave-balances/allocate/
    Yearly allocation endpoint.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, *args, **kwargs):
        serializer = LeaveBalanceAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        from apps.companies.models import Membership

        try:
            membership = Membership.objects.get(
                id=data["membership_id"],
                company=request.company,
            )
        except Membership.DoesNotExist:
            return ApiResponse.error("Employee not found.")

        leave_type = LeaveTypeSelector.get_by_id(
            leave_type_id=data["leave_type_id"],
            company=request.company,
        )
        if not leave_type:
            return ApiResponse.error("Leave type not found.")

        allocated = LeaveBalanceService.yearly_allocation(
            company=request.company,
            membership=membership,
            leave_type=leave_type,
            leave_year=data["leave_year"],
            allocated_days=data["allocated_days"],
        )

        response_serializer = LeaveBalanceDetailSerializer(allocated)
        return ApiResponse.success(data=response_serializer.data)