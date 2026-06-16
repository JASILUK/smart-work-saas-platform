from typing import Dict, List, Type

from apps.attendance.integrations.holidays.base import (
    BaseHolidayProvider,
)
from apps.attendance.integrations.holidays.calendarific_provider import (
    CalendarificHolidayProvider,
)
from apps.attendance.integrations.holidays.exceptions import (
    ProviderNotSupported,
)
from apps.attendance.integrations.holidays.nager_provider import (
    NagerHolidayProvider,
)


class HolidayProviderFactory:
    """
    Central factory responsible for resolving holiday providers.

    Frontend consumers should never choose providers directly.
    The backend selects the most appropriate provider based on
    business rules and regional requirements.
    """

    _registry: Dict[str, Type[BaseHolidayProvider]] = {
        "calendarific": CalendarificHolidayProvider,
        "nager": NagerHolidayProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_name: str,
    ) -> BaseHolidayProvider:
        """
        Explicit provider lookup.

        Primarily intended for internal usage,
        testing, and administrative overrides.
        """

        normalized_name = str(
            provider_name,
        ).strip().lower()

        provider_class = cls._registry.get(
            normalized_name,
        )

        if not provider_class:

            raise ProviderNotSupported(
                f"Holiday provider '{provider_name}' is not supported."
            )

        return provider_class()

    @classmethod
    def get_providers_for_country(
        cls,
        country_code: str,
    ) -> List[BaseHolidayProvider]:
        """
        Returns providers ordered by priority
        for a specific country.

        The import service should iterate through
        this list until one provider succeeds.
        """

        normalized_country = str(
            country_code,
        ).strip().upper()

        if normalized_country == "IN":

            return [
                CalendarificHolidayProvider(),
                NagerHolidayProvider(),
            ]

        return [
            NagerHolidayProvider(),
            CalendarificHolidayProvider(),
        ]