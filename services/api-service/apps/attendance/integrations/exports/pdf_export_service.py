"""
PDF Export Service

Generates professional, printable PDF attendance reports using ReportLab.
All generation happens in-memory via io.BytesIO.

Features:
    - Company logo (if exists, gracefully skipped if not)
    - Company name, report title, generation metadata
    - Applied filters section
    - Summary cards (KPI grid)
    - Employee data table with professional styling
    - Automatic page breaks
    - Repeating table headers on every page
    - Page numbers and footer
    - Professional spacing, margins, and typography
    - Landscape A4 layout optimized for wide tables
"""

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from apps.companies.models import Company


class PDFExportService:
    """
    PDF file generator for attendance reports.

    Produces a landscape A4 PDF optimized for printing and archival.
    Uses ReportLab's Platypus flowable system for automatic pagination.
    """

    # Page configuration
    PAGE_SIZE = landscape(A4)
    PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
    MARGIN = 0.6 * inch

    # Color palette
    PRIMARY_COLOR = colors.HexColor("#1F4E79")
    SECONDARY_COLOR = colors.HexColor("#2E75B6")
    LIGHT_GRAY = colors.HexColor("#F2F2F2")
    MEDIUM_GRAY = colors.HexColor("#E7E6E6")
    DARK_GRAY = colors.HexColor("#404040")
    WHITE = colors.white
    BORDER_COLOR = colors.HexColor("#B4B4B4")

    # Column definitions for the employee table
    TABLE_COLUMNS: list[tuple[str, str, float]] = [
        ("Employee", "user.get_full_name", 1.7),
        ("Dept", "department.name", 1.0),
        ("Title", "job_title", 1.2),
        ("Present", "present_days", 0.7),
        ("Absent", "absent_days", 0.7),
        ("Leave", "leave_days", 0.7),
        ("Late", "late_count", 0.6),
        ("Review", "needs_review", 0.7),
        ("Attnd %", "attendance_percentage", 0.9),
        ("Work Hrs", "total_work_hours", 0.9),
        ("OT Hrs", "overtime_hours", 0.8),
    ]

    @classmethod
    def generate(
        cls,
        *,
        dataset: list[Any],
        summary: dict[str, Any],
        filter_metadata: dict[str, Any],
        company: Company,
    ) -> io.BytesIO:
        """
        Generate a professional PDF report in memory.

        Args:
            dataset: List of annotated Membership objects.
            summary: Dictionary of global summary metrics.
            filter_metadata: Dictionary describing applied filters and generation context.
            company: Tenant Company for branding and optional logo.

        Returns:
            io.BytesIO buffer containing the PDF.
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN,
            rightMargin=cls.MARGIN,
            topMargin=cls.MARGIN,
            bottomMargin=cls.MARGIN,
        )

        # Build the complete flowable story
        story = cls._build_story(
            company=company,
            dataset=dataset,
            summary=summary,
            filter_metadata=filter_metadata,
        )

        doc.build(
            story,
            onFirstPage=cls._draw_page_frame,
            onLaterPages=cls._draw_page_frame,
        )

        buffer.seek(0)
        return buffer

    @classmethod
    def _build_story(
        cls,
        *,
        company: Company,
        dataset: list[Any],
        summary: dict[str, Any],
        filter_metadata: dict[str, Any],
    ) -> list[Any]:
        """
        Construct the list of Platypus flowables that comprise the PDF content.

        Returns:
            List of flowable objects for doc.build().
        """
        story: list[Any] = []
        styles = getSampleStyleSheet()

        # ------------------------------------------------------------------
        # Custom styles
        # ------------------------------------------------------------------
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=cls.PRIMARY_COLOR,
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
        )

        company_style = ParagraphStyle(
            "CompanyName",
            parent=styles["Normal"],
            fontSize=14,
            textColor=cls.PRIMARY_COLOR,
            spaceAfter=2,
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
        )

        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            textColor=cls.DARK_GRAY,
            spaceAfter=10,
            alignment=TA_LEFT,
        )

        section_header_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=cls.PRIMARY_COLOR,
            spaceAfter=4,
            spaceBefore=10,
            fontName="Helvetica-Bold",
        )

        # ------------------------------------------------------------------
        # 1. Company Logo (optional)
        # ------------------------------------------------------------------
        if company.logo and hasattr(company.logo, "path"):
            try:
                img = RLImage(company.logo.path)
                # Scale to max 80px height, maintain aspect ratio
                max_height = 80
                if img.drawHeight > max_height:
                    ratio = max_height / img.drawHeight
                    img.drawHeight = max_height
                    img.drawWidth = img.drawWidth * ratio
                story.append(img)
                story.append(Spacer(1, 6))
            except Exception:
                # Skip logo if any error occurs. Never fail.
                pass

        # ------------------------------------------------------------------
        # 2. Company Name & Report Title
        # ------------------------------------------------------------------
        story.append(Paragraph(company.name, company_style))
        story.append(Paragraph("Attendance Report", title_style))

        # ------------------------------------------------------------------
        # 3. Generation Metadata
        # ------------------------------------------------------------------
        generated_by = filter_metadata.get("generated_by", "")
        generated_at = filter_metadata.get("generated_at", "")

        meta_lines = []
        if generated_by:
            meta_lines.append(f"Generated By: {generated_by}")
        if generated_at:
            meta_lines.append(f"Generated At: {generated_at}")

        meta_lines.append(
            f"Reporting Period: {filter_metadata.get('date_from', 'N/A')} to {filter_metadata.get('date_to', 'N/A')}"
        )

        for line in meta_lines:
            story.append(Paragraph(line, subtitle_style))

        story.append(Spacer(1, 6))

        # ------------------------------------------------------------------
        # 4. Applied Filters
        # ------------------------------------------------------------------
        story.append(Paragraph("Applied Filters", section_header_style))

        filter_data = [
            [
                "Period:",
                f"{filter_metadata.get('date_from', 'N/A')} to {filter_metadata.get('date_to', 'N/A')}",
            ],
            [
                "Month:",
                str(filter_metadata.get("selected_month") or "All"),
            ],
            [
                "Year:",
                str(filter_metadata.get("selected_year") or "All"),
            ],
            [
                "Department:",
                str(filter_metadata.get("selected_department") or "All"),
            ],
        ]

        filter_table = Table(filter_data, colWidths=[1.2 * inch, 3 * inch])
        filter_table.setStyle(
            TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), cls.DARK_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(filter_table)
        story.append(Spacer(1, 10))

        # ------------------------------------------------------------------
        # 5. Summary Cards (KPI Grid)
        # ------------------------------------------------------------------
        story.append(Paragraph("Summary", section_header_style))

        summary_items = [
            ("Total Employees", summary.get("total_employees", 0)),
            ("Present", summary.get("present_employees", 0)),
            ("Absent", summary.get("absent_employees", 0)),
            ("On Leave", summary.get("employees_on_leave", 0)),
            ("Late Arrivals", summary.get("employees_late", 0)),
            (
                "Avg Attendance %",
                f"{summary.get('average_attendance_percentage', 0)}%",
            ),
            ("Total Work Hrs", summary.get("total_work_hours", 0)),
            ("Total OT Hrs", summary.get("total_overtime_hours", 0)),
        ]

        # Build summary cards as a 4-column table
        summary_rows = []
        for i in range(0, len(summary_items), 4):
            row = summary_items[i : i + 4]
            card_style = ParagraphStyle(
                "Card",
                parent=styles["Normal"],
                alignment=TA_CENTER,
                fontSize=9,
                leading=14,
            )
            summary_rows.append(
                [
                    Paragraph(
                        f"<b>{label}</b><br/><font size=13 color='#1F4E79'>{value}</font>",
                        card_style,
                    )
                    for label, value in row
                ]
            )
            # Pad last row if needed
            while len(summary_rows[-1]) < 4:
                summary_rows[-1].append("")

        summary_table = Table(summary_rows, colWidths=[2.0 * inch] * 4)
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), cls.MEDIUM_GRAY),
                ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
                ("GRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # ------------------------------------------------------------------
        # 6. Employee Data Table
        # ------------------------------------------------------------------
        story.append(Paragraph("Employee Details", section_header_style))
        story.append(Spacer(1, 4))

        # Table headers
        headers = [col[0] for col in cls.TABLE_COLUMNS]

        # Table data
        table_data = [headers]
        for row_obj in dataset:
            table_data.append(
                [
                    cls._resolve_attribute(row_obj, col[1])
                    for col in cls.TABLE_COLUMNS
                ]
            )

        # Calculate available width and scale columns proportionally
        available_width = cls.PAGE_WIDTH - (2 * cls.MARGIN)
        total_weight = sum(col[2] for col in cls.TABLE_COLUMNS)
        scaled_widths = [
            (col[2] / total_weight) * available_width for col in cls.TABLE_COLUMNS
        ]

        employee_table = Table(
            table_data, colWidths=scaled_widths, repeatRows=1
        )

        # Professional table styling
        table_style = TableStyle([
            # Header styling
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), cls.WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Body styling
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 1), (2, -1), "LEFT"),  # Name, Dept, Title left
            ("ALIGN", (3, 1), (-1, -1), "CENTER"),  # Numeric columns center
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            # Grid and borders
            ("GRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, cls.PRIMARY_COLOR),
        ])

        # Apply alternating row fills
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.add(
                    "BACKGROUND", (0, i), (-1, i), cls.LIGHT_GRAY
                )

        employee_table.setStyle(table_style)
        story.append(employee_table)

        return story

    @classmethod
    def _draw_page_frame(cls, canvas, doc):
        """
        Draw the page frame, footer, and page number on every page.

        This callback is invoked by SimpleDocTemplate for each page.
        """
        canvas.saveState()

        # Footer line
        footer_y = 0.4 * inch
        canvas.setStrokeColor(cls.BORDER_COLOR)
        canvas.setLineWidth(0.5)
        canvas.line(
            cls.MARGIN,
            footer_y + 10,
            cls.PAGE_WIDTH - cls.MARGIN,
            footer_y + 10,
        )

        # Page number (right)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(cls.DARK_GRAY)
        page_text = f"Page {doc.page}"
        canvas.drawRightString(
            cls.PAGE_WIDTH - cls.MARGIN, footer_y, page_text
        )

        # Confidential footer (left)
        canvas.drawString(
            cls.MARGIN, footer_y, "Confidential - Internal Use Only"
        )

        canvas.restoreState()

    @classmethod
    def _resolve_attribute(cls, obj: Any, attr_path: str) -> Any:
        """
        Resolve a dotted attribute path against an object.

        Special cases:
            - "user.get_full_name" -> f"{first_name} {last_name}"
            - "department.name" -> department name or "N/A"
            - "needs_review" -> "Yes" / "No"
            - "attendance_percentage" -> formatted with % sign

        Args:
            obj: The annotated Membership instance.
            attr_path: Dot-notation path.

        Returns:
            The resolved scalar value, formatted for PDF display.
        """
        if attr_path == "user.get_full_name":
            user = obj.user
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            return name or user.username or "N/A"

        if attr_path == "department.name":
            dept = obj.department
            return dept.name if dept else "N/A"

        if attr_path == "needs_review":
            return "Yes" if obj.needs_review else "No"

        if attr_path == "attendance_percentage":
            val = getattr(obj, attr_path, 0)
            return f"{val}%"

        # Standard attribute resolution
        parts = attr_path.split(".")
        value = obj
        for part in parts:
            value = getattr(value, part, None)
            if value is None:
                return "N/A"
        return value