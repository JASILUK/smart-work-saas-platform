from rest_framework.views import APIView

from apps.companies.api.base import BaseCompanyAPIView
from apps.companies.api.v1.serializers.serializers import (
    EmployeeSerializer,
    EmployeeUpdateSerializer,
)
from apps.companies.selectors.Employee_selectors import EmployeeSelector
from apps.companies.services.emplyee_service import EmployeeService
from apps.core.api_response import ApiResponse


class EmployeeListAPI(BaseCompanyAPIView):
    """
    List company employees or invite a new employee.

    """

    required_permissions = {
        "POST": "tenent.employee.create",
    }

    def get(self, request):
        company = request.company

        employees = EmployeeSelector.list_company_employees(company=company)

        serializer = EmployeeSerializer(employees, many=True)

        return ApiResponse.success(data=serializer.data)


class EmployeeDetailAPI(BaseCompanyAPIView):
    """
    Retrieve, update or delete an employee.
    """

    required_permissions = {
        "GET": "tenant.employee.view",
        "PATCH": "tenant.employee.update",
        "DELETE": "tenant.employee.delete",
    }

    def get(self, request, pk):
        employee = EmployeeSelector.get_employee(
            company=request.company, employee_id=pk
        )
        serializer = EmployeeSerializer(employee)

        return ApiResponse.success(data=serializer.data)

    def patch(self, request, pk):
        """
        Update employee role.
        """

        employee = EmployeeSelector.get_employee(
            company=request.company, employee_id=pk
        )

        serializer = EmployeeUpdateSerializer(employee, data=request.data, partial=True)

        serializer.is_valid()
        service = EmployeeService(company=request.company, user=request.user)
        service.update_employee(employee=employee, data=request.data)

        return ApiResponse.success(data=serializer.data)

    def delete(self, request, pk):
        """
        Remove employee from company.
        """

        employee = EmployeeSelector.get_employee(
            company=request.company, employee_id=pk
        )
        service = EmployeeService(company=request.company, user=request.user)
        service.remove_employee(company=request.company, employee=employee)

        return ApiResponse.success()


class EmployeeBlockAPI(BaseCompanyAPIView):
    """
    Block an employee.
    """

    required_permissions = {"POST": "tenant.employee.block"}

    def post(self, request, pk):

        employee = EmployeeSelector.get_employee(
            company=request.company, employee_id=pk
        )
        service = EmployeeService(company=request.company, user=request.user)
        blocked_user = service.block_employee(employee=employee)
        serializer = EmployeeSerializer(blocked_user)
        return ApiResponse.success(
            data=serializer.data, message="Employee blocked successfully"
        )


class EmployeeUnBlockAPI(BaseCompanyAPIView):
    """
    Unblock an employee.
    """

    required_permissions = {"POST": "tenant.employee.block"}

    def post(self, request, pk):

        employee = EmployeeSelector.get_employee(
            company=request.company, employee_id=pk
        )
        service = EmployeeService(company=request.company, user=request.user)
        updated_user = service.unblock_employee(employee=employee)
        serializer = EmployeeSerializer(updated_user)
        return ApiResponse.success(
            data=serializer.data, message="Employee blocked successfully"
        )
