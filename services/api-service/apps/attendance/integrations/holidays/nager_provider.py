import datetime
from typing import Any, Dict, List, Optional
import requests

from apps.attendance.integrations.holidays.base import BaseHolidayProvider
from apps.attendance.integrations.holidays.constants import NAGER_BASE_URL, REQUEST_TIMEOUT_SECONDS
from apps.attendance.integrations.holidays.exceptions import HolidayImportFailed


class NagerHolidayProvider(BaseHolidayProvider):
    """
    Ingestion bridge for the Nager.Date Public Holiday API engine.
    Handles upstream v3 endpoints and normalizes international calendars into flat system schemas.
    """

    def fetch_holidays(
        self,
        *,
        country_code: str,
        year: int,
        subdivision_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries the Nager statutory database endpoint for a targeted year and country identifier code.
        """
        # Endpoint mapping structure: /PublicHolidays/{year}/{countryCode}
        url = f"{NAGER_BASE_URL}/PublicHolidays/{year}/{country_code.upper()}"
        
        try:
            response = requests.get(
                url=url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"Accept": "application/json"}
            )
            
            # Explicitly raise requests exceptions before executing content parsing loops
            response.raise_for_status()
            raw_data: List[Dict[str, Any]] = response.json()
            
        except requests.RequestException as exc:
            raise HolidayImportFailed(
                f"Nager API network synchronization pipeline aborted due to connectivity failure: {str(exc)}"
            ) from exc
        except ValueError as exc:
            raise HolidayImportFailed(
                f"Nager payload processing blocked due to malformed upstream JSON structures: {str(exc)}"
            ) from exc

        normalized_holidays: List[Dict[str, Any]] = []

        for item in raw_data:
            try:
                # Parse string date markers down to primitive datetime.date instances
                parsed_date = datetime.date.fromisoformat(item["date"])
                
                # Enforce subdivision/regional boundary filtering if requested
                if subdivision_code:
                    counties: Optional[List[str]] = item.get("counties")
                    # If the holiday is regionally restricted and our target code isn't in that list, exclude it
                    if counties is not None and subdivision_code not in counties:
                        continue

                # Fallback assignment picking native localization names where available
                holiday_name = item.get("localName") or item.get("name") or "Public Holiday"

                normalized_payload = {
                    "name": holiday_name,
                    "holiday_date": parsed_date,
                    "holiday_type": "national",
                    "is_paid": True,
                    "external_id": f"nager:{parsed_date.isoformat()}:{holiday_name.replace(' ', '_')}",
                    "provider": "nager",
                }
                normalized_holidays.append(normalized_payload)
                
            except (KeyError, TypeError, ValueError) as exc:
                # Shield the execution block from partial structural format drifts within individual rows
                continue

        return normalized_holidays