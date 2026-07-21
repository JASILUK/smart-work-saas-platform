"""
Attendance Report Export Service

Orchestrates the end-to-end export workflow:
    - Validates export format.
    - Reuses AttendanceReportService to resolve and validate filters.
    - Reuses AttendanceReportSelector output (dataset + summary).
    - Delegates file generation to AttendanceExportFactory.
    - Returns a structured export result with filename, content_type, and file_bytes.

Design guarantees:
    - Zero ORM queries duplicated.
    - Zero HTTP-specific logic.
    - Celery-ready: can be invoked from a background task without modification.
"""

import datetime
from dataclasses import dataclass
from typing import Any

from rest_framework.exceptions import ValidationError

from apps.companies.models import Company
from apps.attendance.services.attendance_report_service import AttendanceReportService
from apps.attendance.integrations.exports.factory import AttendanceExportFactory


@dataclass(frozen=True)
class ExportResult:
    """
    Immutable value object representing a generated export file.

    Attributes:
        filename: The download filename (e.g., "attendance_report_2026_06.csv").
        content_type: The MIME type for the file (e.g., "text/csv").
        file_bytes: The in-memory file content as bytes.
    """
    filename: str
    content_type: str
    file_bytes: bytes


class AttendanceReportExportService:
    """
    Central coordinator for attendance report file exports.

    Maintains strict separation of concerns:
        - Filter resolution  -> AttendanceReportService
        - Data retrieval     -> AttendanceReportSelector (via Service)
        - File generation    -> AttendanceExportFactory
        - Result assembly    -> This service (ExportResult construction)
    """

    # Canonical format identifiers.
    SUPPORTED_FORMATS: frozenset[str] = frozenset({"csv", "xlsx", "pdf"})

    # MIME type mappings per export format.
    CONTENT_TYPES: dict[str, str] = {
        "csv": "text/csv",
        "xlsx": (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        "pdf": "application/pdf",
    }

    @classmethod
    def generate_export(
        cls,
        *,
        company: Company,
        params: dict[str, Any],
        export_format: str,
        generated_by: str = "",
    ) -> ExportResult:
        """
        Generate an export file and return an ExportResult value object.

        Args:
            company: The tenant Company instance (from request.company).
            params: Raw query parameters from the request.
            export_format: Canonical format string (csv, xlsx, or pdf).
            generated_by: Optional identifier of the user generating the report
                (e.g., user.get_full_name() or user.email).

        Returns:
            ExportResult containing filename, content_type, and file_bytes.

        Raises:
            ValidationError: If the export format is unsupported or missing.
            APIException: Re-raised from AttendanceReportService if filters are invalid.
        """
        # ------------------------------------------------------------------
        # 1. Validate export format
        # ------------------------------------------------------------------
        normalized_format = export_format.lower().strip()

        if not normalized_format:
            raise ValidationError(
                {"format": ["Export format is required. Supported: csv, xlsx, pdf."]}
            )

        if normalized_format not in cls.SUPPORTED_FORMATS:
            raise ValidationError(
                {
                    "format": [
                        f"Unsupported format '{export_format}'. "
                        f"Supported formats: csv, xlsx, pdf."
                    ]
                }
            )

        # ------------------------------------------------------------------
        # 2. Reuse AttendanceReportService to resolve filters and fetch data
        # ------------------------------------------------------------------
        # AttendanceReportService.compile_attendance_report handles:
        #   - Date boundary resolution (month/year or explicit range)
        #   - Filter validation (date ordering, department_id, membership_id types)
        #   - Ordering normalization
        #   - Delegation to AttendanceReportSelector for ORM execution
        #
        # We receive the EXACT same dataset and summary the UI report uses.
        queryset, summary, filter_metadata = (
            AttendanceReportService.compile_attendance_report(
                company=company,
                params=params,
            )
        )

        # ------------------------------------------------------------------
        # 3. Force evaluation of the queryset to a list for export generators
        # ------------------------------------------------------------------
        # The queryset is already annotated by the selector. Converting to a
        # list here ensures the database is hit exactly once and the export
        # generators work with plain objects, not a live QuerySet.
        dataset: list[Any] = list(queryset)

        # ------------------------------------------------------------------
        # 4. Enrich filter_metadata with generation context
        # ------------------------------------------------------------------
        filter_metadata["generated_by"] = generated_by
        filter_metadata["generated_at"] = datetime.datetime.now().isoformat()

        # ------------------------------------------------------------------
        # 5. Delegate file generation to the factory
        # ------------------------------------------------------------------
        file_buffer = AttendanceExportFactory.build(
            format=normalized_format,
            dataset=dataset,
            summary=summary,
            filter_metadata=filter_metadata,
            company=company,
        )

        # ------------------------------------------------------------------
        # 6. Construct filename and return ExportResult
        # ------------------------------------------------------------------
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"attendance_report_{timestamp}.{normalized_format}"

        file_bytes = file_buffer.getvalue()

        return ExportResult(
            filename=filename,
            content_type=cls.CONTENT_TYPES[normalized_format],
            file_bytes=file_bytes,
        )