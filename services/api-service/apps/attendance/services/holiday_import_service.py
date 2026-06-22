import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.attendance.integrations.holidays.exceptions import (
    HolidayImportFailed,
)
from apps.attendance.integrations.holidays.factory import (
    HolidayProviderFactory,
)
from apps.attendance.models import Holiday
from apps.attendance.selectors.holiday_selector import HolidaySelector


class HolidayImportService:

    # =====================================================
    # IMPORT HOLIDAYS
    # =====================================================

    @classmethod
    def import_holidays(
        cls,
        *,
        company: Any,
        country_code: str,
        year: int,
        subdivision_code: Optional[str] = None,
        overwrite_existing: bool = False,
    ) -> Dict[str, Any]:

        providers = (
            HolidayProviderFactory
            .get_providers_for_country(
                country_code,
            )
        )

        fetched_holidays: List[Dict[str, Any]] = []
        successful_provider: Optional[str] = None
        provider_errors: List[str] = []

        for provider in providers:

            try:

                fetched_holidays = (
                    provider.fetch_holidays(
                        country_code=country_code,
                        year=year,
                        subdivision_code=subdivision_code,
                    )
                )

                successful_provider = (
                    provider.__class__.__name__
                )

                break

            except HolidayImportFailed as exc:

                provider_errors.append(
                    str(exc)
                )

                continue

        if successful_provider is None:

            raise HolidayImportFailed(
                "All holiday providers failed. "
                f"Errors: {' | '.join(provider_errors)}"
            )

        total_received = len(
            fetched_holidays,
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        if total_received == 0:

            return {
                "provider": successful_provider,
                "year": year,
                "country_code": country_code,
                "subdivision_code": subdivision_code,
                "total_received": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
            }

        existing_qs = (
            HolidaySelector
            .get_company_holidays(
                company=company,
            )
        )

        existing_holidays_cache: Dict[
            tuple,
            Holiday,
        ] = {

            (
                holiday.holiday_date,
                holiday.name.lower(),
            ): holiday

            for holiday in existing_qs
        }

        holidays_to_create: List[
            Holiday
        ] = []

        holidays_to_update: List[
            Holiday
        ] = []

        for item in fetched_holidays:

            name = item[
                "name"
            ]

            holiday_date = item[
                "holiday_date"
            ]

            holiday_type = item[
                "holiday_type"
            ]

            is_paid = item[
                "is_paid"
            ]

            external_id = item[
                "external_id"
            ]

            provider_key = item[
                "provider"
            ]

            lookup_key = (
                holiday_date,
                name.lower(),
            )

            existing_holiday = (
                existing_holidays_cache.get(
                    lookup_key,
                )
            )

            # =====================================================
            # CHANGER INSIDE: HolidayImportService.import_holidays
            # =====================================================

            # Locate this inner conditional block inside your fetched_holidays loop:
            if existing_holiday:
                if not overwrite_existing:
                    skipped_count += 1
                    continue

                has_changes = False
                
                # FIXED: Initialize as empty list. Let TimeStampedModel handle the timestamps automatically!
                update_fields = []

                if existing_holiday.holiday_type != holiday_type:
                    existing_holiday.holiday_type = holiday_type
                    update_fields.append("holiday_type")
                    has_changes = True

                if existing_holiday.is_paid != is_paid:
                    existing_holiday.is_paid = is_paid
                    update_fields.append("is_paid")
                    has_changes = True

                if existing_holiday.external_id != external_id:
                    existing_holiday.external_id = external_id
                    update_fields.append("external_id")
                    has_changes = True

                if existing_holiday.provider != provider_key:
                    existing_holiday.provider = provider_key
                    update_fields.append("provider")
                    has_changes = True

                if has_changes:
                    # Include modified dynamically only if your concrete base class permits it, 
                    # otherwise leave it out as Django will handle it natively.
                    setattr(existing_holiday, "_update_fields", update_fields)
                    holidays_to_update.append(existing_holiday)
                    updated_count += 1
                else:
                    skipped_count += 1

            else:

                holiday = Holiday(

                    company=company,

                    name=name,

                    holiday_date=holiday_date,

                    holiday_type=holiday_type,

                    description="",

                    is_paid=is_paid,

                    is_half_day=False,

                    external_id=external_id,

                    provider=provider_key,
                )

                holidays_to_create.append(
                    holiday,
                )

                existing_holidays_cache[
                    lookup_key
                ] = holiday

                created_count += 1

        with transaction.atomic():

            if holidays_to_create:

                Holiday.objects.bulk_create(
                    holidays_to_create,
                    batch_size=500,
                )

            for holiday in holidays_to_update:

                holiday.save(
                    update_fields=getattr(
                        holiday,
                        "_update_fields",
                        [],
                    ),
                )

        return {

            "provider": successful_provider,

            "year": year,

            "country_code": country_code,

            "subdivision_code": subdivision_code,

            "total_received": total_received,

            "created": created_count,

            "updated": updated_count,

            "skipped": skipped_count,
        }

    # =====================================================
    # PREVIEW HOLIDAYS
    # =====================================================

    @classmethod
    def preview_holidays(
        cls,
        *,
        country_code: str,
        year: int,
        subdivision_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        providers = (
            HolidayProviderFactory
            .get_providers_for_country(
                country_code,
            )
        )

        provider_errors: List[
            str
        ] = []

        for provider in providers:

            try:

                return provider.fetch_holidays(
                    country_code=country_code,
                    year=year,
                    subdivision_code=subdivision_code,
                )

            except HolidayImportFailed as exc:

                provider_errors.append(
                    str(exc)
                )

                continue

        raise HolidayImportFailed(
            "Unable to preview holidays. "
            f"Errors: {' | '.join(provider_errors)}"
        )