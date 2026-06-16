import datetime
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from apps.attendance.integrations.holidays.base import BaseHolidayProvider
from apps.attendance.integrations.holidays.constants import (
    REQUEST_TIMEOUT_SECONDS,
)
from apps.attendance.integrations.holidays.exceptions import (
    HolidayImportFailed,
)


class CalendarificHolidayProvider(
    BaseHolidayProvider,
):
    """
    Calendarific holiday provider.

    Primary provider for countries requiring regional/state
    holiday support (e.g. India).

    Normalizes Calendarific responses into the internal
    holiday schema consumed by HolidayImportService.
    """

    BASE_URL = "https://calendarific.com/api/v2/holidays"

    def fetch_holidays(
        self,
        *,
        country_code: str,
        year: int,
        subdivision_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch holidays from Calendarific.

        Examples:

        India National:
            country_code="IN"

        Kerala:
            country_code="IN"
            subdivision_code="IN-KL"

        California:
            country_code="US"
            subdivision_code="US-CA"
        """

        api_key = getattr(
            settings,
            "CALENDARIFIC_API_KEY",
            "",
        )

        if not api_key:
            raise HolidayImportFailed(
                "Calendarific API key is not configured."
            )

        params = {
            "api_key": api_key,
            "country": country_code.upper(),
            "year": year,
        }

        if subdivision_code:
            params["location"] = subdivision_code

        try:

            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={
                    "Accept": "application/json",
                },
            )

            response.raise_for_status()

            payload = response.json()

        except requests.RequestException as exc:

            raise HolidayImportFailed(
                f"Calendarific synchronization failed due "
                f"to connectivity issues: {str(exc)}"
            ) from exc

        except ValueError as exc:

            raise HolidayImportFailed(
                f"Calendarific returned malformed JSON: "
                f"{str(exc)}"
            ) from exc

        holidays = (
            payload
            .get("response", {})
            .get("holidays", [])
        )

        normalized_holidays: List[Dict[str, Any]] = []

        for item in holidays:

            try:

                iso_date = (
                    item["date"]["iso"]
                    .split("T")[0]
                )

                holiday_date = (
                    datetime.date.fromisoformat(
                        iso_date,
                    )
                )

                holiday_name = (
                    item.get("name")
                    or item.get("description")
                    or "Public Holiday"
                )

                holiday_type = "national"

                item_types = item.get(
                    "type",
                    [],
                )

                if (
                    isinstance(item_types, list)
                    and "local" in [
                        str(t).lower()
                        for t in item_types
                    ]
                ):
                    holiday_type = "state"

                normalized_holidays.append(
                    {
                        "name": holiday_name,
                        "holiday_date": holiday_date,
                        "holiday_type": holiday_type,
                        "is_paid": True,
                        "external_id": (
                            f"calendarific:"
                            f"{holiday_date.isoformat()}:"
                            f"{holiday_name.replace(' ', '_')}"
                        ),
                        "provider": "calendarific",
                    }
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

        return normalized_holidays