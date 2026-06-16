from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from apps.attendance.models.company_work_schedule import (
    CompanyWorkSchedule,
)
from apps.attendance.models.shift import (
    Shift,
)
from apps.attendance.validators.working_schedule_validator import (
    WorkingScheduleValidator,
)


class CompanyWorkScheduleValidationMixin:

    # =====================================================
    # WORKING DAYS
    # =====================================================

    def validate_working_days(self, value):

        try:

            return (
                WorkingScheduleValidator
                .normalize_working_days(value)
            )

        except DjangoValidationError as exc:

            raise serializers.ValidationError(
                exc.messages,
            ) from exc

    # =====================================================
    # TIMEZONE
    # =====================================================

    def validate_timezone(self, value):

        try:

            return (
                WorkingScheduleValidator
                .normalize_timezone(value)
            )

        except DjangoValidationError as exc:

            raise serializers.ValidationError(
                exc.messages,
            ) from exc

    # =====================================================
    # WORK HOURS
    # =====================================================

    def validate(self, attrs):

        if self.instance:

            start_time = attrs.get(
                "work_start_time",
                self.instance.work_start_time,
            )

            end_time = attrs.get(
                "work_end_time",
                self.instance.work_end_time,
            )

        else:

            start_time = attrs.get(
                "work_start_time",
            )

            end_time = attrs.get(
                "work_end_time",
            )

        try:

            WorkingScheduleValidator.validate_work_hours(
                work_start_time=start_time,
                work_end_time=end_time,
            )

        except DjangoValidationError as exc:

            raise serializers.ValidationError(
                {
                    "work_end_time": exc.messages,
                }
            ) from exc

        return attrs


class CompanyWorkScheduleCreateSerializer(
    CompanyWorkScheduleValidationMixin,
    serializers.ModelSerializer,
):

    default_shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects.all(),
        required=False,
        allow_null=True,
    )
    
    country = serializers.CharField(
        required=False,
    )

    state = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    timezone = serializers.CharField(
        required=False,
    )

    holiday_provider = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    class Meta:

        model = CompanyWorkSchedule

        fields = [
            "working_days",
            "work_start_time",
            "work_end_time",
            "break_minutes",
            "timezone",
            "country",
            "state",
            "default_shift",
            "holiday_sync_enabled",
            "holiday_provider",
            "is_active",
        ]



class CompanyWorkScheduleUpdateSerializer(
    CompanyWorkScheduleValidationMixin,
    serializers.ModelSerializer,
):

    working_days = serializers.JSONField(
        required=False,
    )

    work_start_time = serializers.TimeField(
        required=False,
    )

    work_end_time = serializers.TimeField(
        required=False,
    )

    break_minutes = serializers.IntegerField(
        required=False,
        min_value=0,
    )

    timezone = serializers.CharField(
        required=False,
    )

    country = serializers.CharField(
        required=False,
    )

    state = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    default_shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects.all(),
        required=False,
        allow_null=True,
    )

    holiday_sync_enabled = serializers.BooleanField(
        required=False,
    )

    holiday_provider = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    is_active = serializers.BooleanField(
        required=False,
    )

    class Meta:

        model = CompanyWorkSchedule

        fields = [
            "working_days",
            "work_start_time",
            "work_end_time",
            "break_minutes",
            "timezone",
            "country",
            "state",
            "default_shift",
            "holiday_sync_enabled",
            "holiday_provider",
            "is_active",
        ]



class CompanyWorkScheduleDetailSerializer(
    serializers.ModelSerializer,
):

    default_shift = serializers.SerializerMethodField()

    class Meta:

        model = CompanyWorkSchedule

        fields = [
            "id",
            "working_days",
            "weekend_days",
            "work_start_time",
            "work_end_time",
            "break_minutes",
            "timezone",
            "country",
            "state",
            "holiday_sync_enabled",
            "holiday_provider",
            "is_active",
            "default_shift",
            "created_at",
            "updated_at",
        ]

    def get_default_shift(self, obj):

        if not obj.default_shift_id:
            return None

        return {
            "id": obj.default_shift_id,
            "name": obj.default_shift.name,
        }