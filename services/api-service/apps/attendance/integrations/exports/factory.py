"""
Attendance Export Factory

Factory pattern implementation for dispatching to the correct
file generation service based on the requested export format.

Responsibilities:
    - Receive format, dataset, summary, filter_metadata, and company.
    - Instantiate and invoke the appropriate export service.
    - Return the generated in-memory file buffer (BytesIO).
"""

import io
from typing import Any

from apps.companies.models import Company
from apps.attendance.integrations.exports.csv_export_service import CSVExportService
from apps.attendance.integrations.exports.excel_export_service import ExcelExportService
from apps.attendance.integrations.exports.pdf_export_service import PDFExportService


class AttendanceExportFactory:
    """
    Factory for attendance report export file generation.

    Maps canonical format strings to their respective export service
    implementations and delegates generation.
    """

    # Registry mapping format identifiers to service classes.
    _registry: dict[str, type] = {
        "csv": CSVExportService,
        "xlsx": ExcelExportService,
        "pdf": PDFExportService,
    }

    @classmethod
    def build(
        cls,
        *,
        format: str,
        dataset: list[Any],
        summary: dict[str, Any],
        filter_metadata: dict[str, Any],
        company: Company,
    ) -> io.BytesIO:
        """
        Build and return an in-memory file buffer for the requested format.

        Args:
            format: Canonical export format (csv, xlsx, pdf).
            dataset: List of annotated Membership objects (employee rows).
            summary: Dictionary of global summary metrics.
            filter_metadata: Dictionary describing applied filters and generation context.
            company: The tenant Company instance for header branding.

        Returns:
            io.BytesIO buffer containing the generated file.

        Raises:
            ValueError: If the format is not registered (defensive; should be
                        pre-validated by AttendanceReportExportService).
        """
        service_class = cls._registry.get(format)

        if service_class is None:
            raise ValueError(
                f"No export service registered for format: {format}. "
                f"Registered formats: {list(cls._registry.keys())}"
            )

        # Instantiate and delegate generation.
        # Each service receives the full context needed for professional output.
        return service_class.generate(
            dataset=dataset,
            summary=summary,
            filter_metadata=filter_metadata,
            company=company,
        )