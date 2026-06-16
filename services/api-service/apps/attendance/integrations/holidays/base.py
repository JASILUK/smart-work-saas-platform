import abc
import datetime
from typing import Any, Dict, List, Optional


class BaseHolidayProvider(abc.ABC):
    """
    Abstract Base Class establishing structural interface contracts for all external 
    public holiday aggregation engines. Ensures complete protocol normalization across providers.
    """

    @abc.abstractmethod
    def fetch_holidays(
        self,
        *,
        country_code: str,
        year: int,
        subdivision_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a network fetch against an upstream provider and returns a uniform schema.

        Expected Output Structure:
        [
            {
                "name": str,
                "holiday_date": datetime.date,
                "holiday_type": str,
                "is_paid": bool,
                "external_id": str,
                "provider": str,
            }
        ]
        """
        raise NotImplementedError("Subclasses must implement fetch_holidays method.")