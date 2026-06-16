from rest_framework import serializers
from apps.attendance.models import Holiday
import datetime
from typing import Optional


# =====================================================
# 1. HOLIDAY CREATE SERIALIZER
# =====================================================

class HolidayCreateSerializer(serializers.ModelSerializer):
    """
    Handles payload data validation for HR professionals manually declaring 
    a localized corporate or calendar holiday entity.
    """
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        default=""
    )
    is_paid = serializers.BooleanField(
        required=False, 
        default=True
    )
    is_half_day = serializers.BooleanField(
        required=False, 
        default=False
    )

    class Meta:
        model = Holiday
        fields = [
            "name",
            "holiday_type",
            "holiday_date",
            "description",
            "is_paid",
            "is_half_day",
        ]

    def validate_name(self, value: str) -> str:
        """Ensures the descriptive holiday designation label is not left blank."""
        if not value or str(value).strip() == "":
            raise serializers.ValidationError("Holiday name cannot be blank.")
        return value


# =====================================================
# 2. HOLIDAY UPDATE SERIALIZER
# =====================================================

class HolidayUpdateSerializer(serializers.ModelSerializer):
    """
    Facilitates structured partial changes on pre-existing holiday rows 
    while preserving edge constraint verifications.
    """
    name = serializers.CharField(required=False)
    holiday_type = serializers.ChoiceField(
        choices=Holiday.HolidayType.choices, 
        required=False
    )
    holiday_date = serializers.DateField(required=False)
    description = serializers.CharField(
        required=False, 
        allow_blank=True
    )
    is_paid = serializers.BooleanField(required=False)
    is_half_day = serializers.BooleanField(required=False)

    class Meta:
        model = Holiday
        fields = [
            "name",
            "holiday_type",
            "holiday_date",
            "description",
            "is_paid",
            "is_half_day",
        ]

    def validate_name(self, value: str) -> str:
        """Validates that a modified holiday name is non-empty if supplied in payload."""
        if value is not None and str(value).strip() == "":
            raise serializers.ValidationError("Holiday name cannot be blank.")
        return value


# =====================================================
# 3. HOLIDAY DETAIL SERIALIZER
# =====================================================

class HolidayDetailSerializer(serializers.ModelSerializer):
    """
    Constructs high-fidelity payload schemas exposing granular fields 
    for administrative verification boards.
    """
    provider = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(source="modified", read_only=True)

    class Meta:
        model = Holiday
        fields = [
            "id",
            "name",
            "holiday_type",
            "holiday_date",
            "description",
            "is_paid",
            "is_half_day",
            "provider",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_provider(self, obj: Holiday) -> Optional[str]:
        """Ensures that empty or omitted string providers map as clean JSON null objects."""
        return obj.provider if obj.provider else None


# =====================================================
# 4. HOLIDAY LIST SERIALIZER
# =====================================================

class HolidayListSerializer(serializers.ModelSerializer):
    """
    Provides optimized, minimal payload arrays to feed frontend tables, 
    time-off dropdowns, and dashboard calendar displays.
    """
    class Meta:
        model = Holiday
        fields = [
            "id",
            "name",
            "holiday_type",
            "holiday_date",
            "is_paid",
            "is_half_day",
        ]
        read_only_fields = fields


    


# =====================================================
# 1. HOLIDAY IMPORT REQUEST SERIALIZER
# =====================================================

class HolidayImportRequestSerializer(
    serializers.Serializer,
):

    country_code = serializers.CharField(
        max_length=2,
        required=True,
        error_messages={
            "required": (
                "A two-letter ISO country code "
                "is required."
            ),
        },
    )

    year = serializers.IntegerField(
        required=True,
        error_messages={
            "required": (
                "A target calendar year "
                "must be specified."
            ),
        },
    )

    subdivision_code = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )

    overwrite_existing = serializers.BooleanField(
        required=False,
        default=False,
    )

    def validate_country_code(
        self,
        value: str,
    ) -> str:

        value = (
            str(value)
            .strip()
            .upper()
        )

        if (
            len(value) != 2
            or not value.isalpha()
        ):

            raise serializers.ValidationError(
                "The country code must be a valid "
                "ISO 3166-1 alpha-2 code."
            )

        return value

    def validate_year(
        self,
        value: int,
    ) -> int:

        current_year = (
            datetime.datetime.now().year
        )

        max_allowed_year = (
            current_year + 2
        )

        if value < 2000:

            raise serializers.ValidationError(
                "Imports are not supported "
                "for years before 2000."
            )

        if value > max_allowed_year:

            raise serializers.ValidationError(
                f"Imports are restricted to "
                f"{max_allowed_year}."
            )

        return value

    def validate_subdivision_code(
        self,
        value: str,
    ) -> str | None:

        if value in (
            None,
            "",
        ):

            return None

        return (
            str(value)
            .strip()
            .upper()
        )


# =====================================================
# 2. HOLIDAY PREVIEW REQUEST SERIALIZER
# =====================================================

class HolidayPreviewRequestSerializer(
    serializers.Serializer,
):

    country_code = serializers.CharField(
        max_length=2,
        required=True,
        error_messages={
            "required": (
                "A two-letter ISO country code "
                "is required."
            ),
        },
    )

    year = serializers.IntegerField(
        required=True,
        error_messages={
            "required": (
                "A target calendar year "
                "must be specified."
            ),
        },
    )

    subdivision_code = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )

    def validate_country_code(
        self,
        value: str,
    ) -> str:

        value = (
            str(value)
            .strip()
            .upper()
        )

        if (
            len(value) != 2
            or not value.isalpha()
        ):

            raise serializers.ValidationError(
                "The country code must be a valid "
                "ISO 3166-1 alpha-2 code."
            )

        return value

    def validate_year(
        self,
        value: int,
    ) -> int:

        current_year = (
            datetime.datetime.now().year
        )

        max_allowed_year = (
            current_year + 2
        )

        if value < 2000:

            raise serializers.ValidationError(
                "Previews are not supported "
                "for years before 2000."
            )

        if value > max_allowed_year:

            raise serializers.ValidationError(
                f"Previews are restricted to "
                f"{max_allowed_year}."
            )

        return value

    def validate_subdivision_code(
        self,
        value: str,
    ) -> str | None:

        if value in (
            None,
            "",
        ):

            return None

        return (
            str(value)
            .strip()
            .upper()
        )


# =====================================================
# 3. HOLIDAY IMPORT SUMMARY SERIALIZER
# =====================================================

class HolidayImportSummarySerializer(
    serializers.Serializer,
):

    provider = serializers.CharField(
        read_only=True,
    )

    year = serializers.IntegerField(
        read_only=True,
    )

    country_code = serializers.CharField(
        read_only=True,
    )

    subdivision_code = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    total_received = serializers.IntegerField(
        read_only=True,
    )

    created = serializers.IntegerField(
        read_only=True,
    )

    updated = serializers.IntegerField(
        read_only=True,
    )

    skipped = serializers.IntegerField(
        read_only=True,
    )