from typing import Any, Dict, List
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.attendance.models import Holiday
from apps.attendance.selectors import holiday_selector


class HolidayService:
    """
    Service class handling all write operations (create, update, delete, bulk import)
    for the Holiday module. Acts as the single source of truth for business logic mutations.
    """

    # =====================================================
    # CREATE HOLIDAY
    # =====================================================

    @staticmethod
    def create_holiday(
        *,
        company: Any,
        actor: Any,
        validated_data: Dict[str, Any],
    ) -> Holiday:
        """
        Creates a new holiday record for a company. 
        Prevents duplicates on the same date with the same name via strict pre-flight checks.
        """
        name = validated_data["name"]
        holiday_date = validated_data["holiday_date"]

        if holiday_selector.holiday_exists(company=company, holiday_date=holiday_date, name=name):
            raise ValidationError("This holiday already exists.")

        with transaction.atomic():
            holiday = Holiday.objects.create(
                company=company,
                **validated_data
            )
        return holiday

    # =====================================================
    # UPDATE HOLIDAY
    # =====================================================

    @staticmethod
    def update_holiday(
        *,
        holiday: Holiday,
        actor: Any,
        validated_data: Dict[str, Any],
    ) -> Holiday:
        """
        Updates specific attributes of an existing holiday.
        Re-validates uniqueness invariants if identity or chronological markers mutate.
        """
        name = validated_data.get("name", holiday.name)
        holiday_date = validated_data.get("holiday_date", holiday.holiday_date)

        if name != holiday.name or holiday_date != holiday.holiday_date:
            duplicate_exists = Holiday.objects.filter(
                company=holiday.company,
                holiday_date=holiday_date,
                name__iexact=name
            ).exclude(id=holiday.id).exists()

            if duplicate_exists:
                raise ValidationError("This holiday already exists.")

        update_fields = []
        for field, value in validated_data.items():
            if hasattr(holiday, field):
                setattr(holiday, field, value)
                update_fields.append(field)

        if update_fields:
            if hasattr(holiday, "modified"):
                update_fields.append("modified")
            holiday.save(update_fields=update_fields)

        return holiday

    # =====================================================
    # DELETE HOLIDAY
    # =====================================================

    @staticmethod
    def delete_holiday(
        *,
        holiday: Holiday,
        actor: Any,
    ) -> bool:
        """
        Atomically removes a holiday entry, restoring the target calendar date 
        back to standard operational shift tracking rules.
        """
        with transaction.atomic():
            holiday.delete()
        return True

    # =====================================================
    # IMPORT HOLIDAY
    # =====================================================

    @staticmethod
    def import_holiday(
        *,
        company: Any,
        actor: Any,
        holiday_data: Dict[str, Any],
    ) -> Holiday:
        """
        Idempotently ingests an external API provider holiday object. 
        Safely skips execution if records match company uniqueness keys to support smooth updates.
        """
        name = holiday_data["name"]
        holiday_date = holiday_data["holiday_date"]

        existing_holidays = holiday_selector.get_holiday_by_date(company=company, holiday_date=holiday_date)
        matching_holiday = existing_holidays.filter(name__iexact=name).first()

        if matching_holiday:
            return matching_holiday

        with transaction.atomic():
            holiday = Holiday.objects.create(
                company=company,
                **holiday_data
            )
        return holiday

    # =====================================================
    # BULK IMPORT HOLIDAYS
    # =====================================================

    @staticmethod
    def bulk_import_holidays(
        *,
        company: Any,
        actor: Any,
        holidays: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Performs an enterprise-wide compliance ingestion pipeline optimized for high performance.
        
        PERFORMANCE RESOLUTIONS:
        - Eliminates N+1 database queries by fetching all company holidays up front.
        - Uses an in-memory dictionary cache map for O(1) duplicate checks.
        - Replaces individual .create() saves with a single unified SQL bulk_create statement.
        """
        imported_count = 0
        skipped_count = 0
        
        if not holidays:
            return {"imported": imported_count, "skipped": skipped_count}

        # Step 1: Query existing holidays once to pre-populate our memory map cache
        existing_holidays_qs = holiday_selector.get_company_holidays(company=company).values_list(
            "holiday_date", "name"
        )
        
        # Store combinations as a hashed set key format: {(date, "republic day"), ...}
        existing_holidays_map = {
            (h_date, h_name.lower()) for h_date, h_name in existing_holidays_qs
        }

        holidays_to_create = []
        
        # Step 2: Evaluate changes in-memory (Zero SQL executed inside this loop)
        for holiday_data in holidays:
            name_lower = holiday_data["name"].lower()
            holiday_date = holiday_data["holiday_date"]
            lookup_key = (holiday_date, name_lower)

            if lookup_key in existing_holidays_map:
                skipped_count += 1
            else:
                # Instantiate the model object in memory without calling the database yet
                new_holiday = Holiday(company=company, **holiday_data)
                holidays_to_create.append(new_holiday)
                
                # Append to our local memory map tracking context to prevent internal duplicates within the payload itself
                existing_holidays_map.add(lookup_key)
                imported_count += 1

        # Step 3: Run a single transaction chunked bulk write to the database
        if holidays_to_create:
            with transaction.atomic():
                Holiday.objects.bulk_create(holidays_to_create, batch_size=500)

        return {
            "imported": imported_count,
            "skipped": skipped_count,
        }