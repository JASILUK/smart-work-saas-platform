# apps/attendance/api/v1/serializers/hr_report_serializers.py
from rest_framework import serializers
from apps.attendance.models.report_models import HRReportGenerationHistory, HRReportAutomationSchedule

class HRReportSummaryMetricsSerializer(serializers.Serializer):
    total_attendance_records = serializers.IntegerField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    half_day = serializers.IntegerField()
    leave = serializers.IntegerField()
    holiday = serializers.IntegerField()
    weekend = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
    average_working_hours = serializers.FloatField()
    average_break_hours = serializers.FloatField()
    average_check_in = serializers.CharField()
    average_check_out = serializers.CharField()
    average_late_minutes = serializers.FloatField()
    average_overtime = serializers.FloatField()
    needs_review_count = serializers.IntegerField()
    auto_closed_count = serializers.IntegerField()

class HRPayrollSummaryRowSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()
    first_name = serializers.CharField(source="membership__user__first_name")
    last_name = serializers.CharField(source="membership__user__last_name")
    username = serializers.CharField(source="membership__user__username")
    department_name = serializers.CharField(source="membership__department__name", default="Unassigned")
    scheduled_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    half_days = serializers.IntegerField()
    weekend_count = serializers.IntegerField()
    holiday_count = serializers.IntegerField()
    total_working_hours = serializers.SerializerMethodField()
    total_overtime_hours = serializers.SerializerMethodField()

    def get_total_working_hours(self, obj) -> float:
        return round((obj["total_work_minutes_sum"] or 0) / 60.0, 2)

    def get_total_overtime_hours(self, obj) -> float:
        return round((obj["total_overtime_minutes_sum"] or 0) / 60.0, 2)

class HRReportExportTriggerInputSerializer(serializers.Serializer):
    report_type = serializers.CharField(max_length=100, default="COMPANY_SUMMARY")
    format = serializers.ChoiceField(choices=["CSV", "EXCEL", "PDF"], default="CSV")
    filters = serializers.JSONField(required=True)

class HRReportScheduleInputSerializer(serializers.Serializer):
    report_type = serializers.CharField(max_length=100, required=True)
    frequency = serializers.ChoiceField(choices=["DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"], required=True)
    format = serializers.ChoiceField(choices=["CSV", "EXCEL", "PDF"], default="CSV")
    recipients = serializers.ListField(child=serializers.EmailField(), required=True)
    filters = serializers.JSONField(default=dict)

class HRReportGenerationHistorySerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source="generated_by.user.get_full_name", default="Automated System")

    class Meta:
        model = HRReportGenerationHistory
        fields = ["id", "report_type", "export_format", "status", "file_url", "error_message", "generated_by_name", "created_at"]