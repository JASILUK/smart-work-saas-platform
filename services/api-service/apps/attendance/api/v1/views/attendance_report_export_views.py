"""
Attendance Report Export API Controller

Provides enterprise-grade file export endpoints for attendance reports.
Supports CSV, Excel (.xlsx), and PDF formats with identical filtering
semantics as the AttendanceReportAPIView.
"""

import io
from typing import Any

from django.http import FileResponse
from rest_framework.request import Request

from apps.companies.api.base import BaseCompanyAPIView
from apps.attendance.services.attendance_report_export_service import (
    AttendanceReportExportService,
)


class AttendanceReportExportAPIView(BaseCompanyAPIView):
    """
    Export attendance reports as downloadable files (CSV, XLSX, PDF).

    SECURITY NOTE:
        We use `export_format` instead of `format` as the query parameter
        because DRF's content negotiation intercepts `?format=...` for
        renderer selection (JSON, Browsable API). Using `format` causes
        Http404 when no renderer matches the requested format (e.g., csv).
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request: Request, *args, **kwargs) -> FileResponse:
        """
        Handle GET requests for attendance report exports.

        Query Parameters:
            export_format: File format — csv, xlsx, or pdf (required)
            All other filters from AttendanceReportAPIView (month, year, etc.)

        Returns:
            FileResponse with the generated export file as attachment.
        """
        # ------------------------------------------------------------------
        # 1. Extract query parameters
        # ------------------------------------------------------------------
        query_params: dict[str, Any] = request.query_params.dict()

        # CRITICAL: Use `export_format` NOT `format` to avoid DRF content
        # negotiation conflict. DRF's `?format=...` is reserved for renderer
        # selection (json, api). Passing `?format=csv` raises Http404
        # because no renderer is registered for the `csv` format suffix.
        export_format: str | None = query_params.get("export_format")

        # ------------------------------------------------------------------
        # 2. Extract generating user identifier
        # ------------------------------------------------------------------
        generated_by = ""
        user = request.user
        if user and user.is_authenticated:
            generated_by = (
                user.get_full_name()
                or getattr(user, "username", None)
                or str(user)
            )

        # ------------------------------------------------------------------
        # 3. Delegate to export service
        # ------------------------------------------------------------------
        export_result = AttendanceReportExportService.generate_export(
            company=request.company,
            params=query_params,
            export_format=export_format or "",
            generated_by=generated_by,
        )

        # ------------------------------------------------------------------
        # 4. Return FileResponse
        # ------------------------------------------------------------------
        return FileResponse(
            io.BytesIO(export_result.file_bytes),
            content_type=export_result.content_type,
            as_attachment=True,
            filename=export_result.filename,
        )