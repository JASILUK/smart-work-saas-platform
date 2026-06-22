import datetime
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.companies.models import (Company,Membership)
from apps.attendance.models.face_enrollment import FaceEnrollment
 

User = get_user_model()

class TestEmployeeDashboardAPI(APITestCase):

    def setUp(self):
        self.company_a = Company.objects.create(name="Company Alpha", domain="alpha.com")
        self.company_b = Company.objects.create(name="Company Beta", domain="beta.com")

        self.user_a = User.objects.create_user(username="johndoe", email="john@alpha.com", password="password123")
        self.user_b = User.objects.create_user(username="janedoe", email="jane@beta.com", password="password123")

        self.membership_a = Membership.objects.create(company=self.company_a, user=self.user_a, role="EMPLOYEE")
        self.membership_b = Membership.objects.create(company=self.company_b, user=self.user_b, role="EMPLOYEE")

        self.url = reverse("attendance-dashboard")

    @patch("apps.attendance.services.employee_dashboard_service.EmployeeDashboardService.get_dashboard")
    @patch("apps.shared.api.views.BaseCompanyAPIView.check_permissions")
    def test_dashboard_endpoint_success_contract_shape(self, mock_check_perms, mock_service):
        mock_check_perms.return_value = True
        mock_service.return_value = {
            "employee": {"name": "John Doe", "username": "johndoe"},
            "today": {"status": "NOT_CHECKED_IN", "check_in": "", "check_out": "", "working_minutes": 0, "shift": None},
            "attendance_access": {"auto_synced": False, "primary_method": "WEB", "available_methods": ["WEB"], "gps_required": False, "face_enrollment_status": "NO_ENROLLMENT"},
            "actions": {"can_check_in": True, "can_check_out": False, "can_start_break": False, "can_resume_break": False},
            "monthly_summary": {"present_days": 5, "late_days": 1, "absent_days": 0, "overtime_hours": 2.5},
            "pending_requests": {"count": 0, "items": []},
            "leave_balance": {"enabled": False, "balances": []},
            "upcoming": {"next_holiday": None, "next_shift": None}
        }

        self.client.force_authenticate(user=self.user_a)
        # Inject tenant contexts inside request scopes manually mock-adapted to BaseCompanyAPIView expectations
        with patch.object(Company, 'objects', lambda: Company.objects), \
             patch('apps.shared.api.middleware.TenantMiddleware') as mock_middleware:
            
            response = self.client.get(self.url, HTTP_X_COMPANY_ID=str(self.company_a.id))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("data", response.data)
            self.assertEqual(response.data["data"]["employee"]["username"], "johndoe")

    @patch("apps.attendance.services.employee_dashboard_service.EmployeeDashboardService.get_dashboard")
    def test_cross_tenant_isolation_guardrails(self, mock_service):
        self.client.force_authenticate(user=self.user_a)
        # Attempting query parsing context directed to Company Beta environment indexes
        response = self.client.get(self.url, HTTP_X_COMPANY_ID=str(self.company_b.id))
        # BaseCompanyAPIView context matching evaluates membership domain safe locks throwing 403 or 401 hooks
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])