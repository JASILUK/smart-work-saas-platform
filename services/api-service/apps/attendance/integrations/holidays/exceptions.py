# apps/attendance/integrations/holidays/exceptions.py
from apps.core.exceptions import ApplicationError

class HolidayProviderError(ApplicationError):
    """Base class for all holiday integration errors."""
    def __init__(self, message: str, code: str = "holiday_provider_error", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class ProviderNotSupported(HolidayProviderError):
    def __init__(self, provider_name: str):
        super().__init__(
            message=f"The holiday provider '{provider_name}' is not supported by this tenant engine.",
            code="provider_not_supported",
            status_code=400
        )


class HolidayImportFailed(HolidayProviderError):
    def __init__(self, details: str):
        super().__init__(
            message=f"The upstream holiday synchronization pipeline failed: {details}",
            code="holiday_import_failed",
            status_code=502,  # 502 Bad Gateway is perfect for third-party API failures!
        )