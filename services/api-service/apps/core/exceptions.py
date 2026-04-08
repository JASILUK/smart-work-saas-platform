# core/exceptions.pyf
from rest_framework import status


class ApplicationError(Exception):
    """Base class for all business logic errors in the SaaS."""

    def __init__(self, message: str, code: str = "bad_request", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class UserAlreadyExistsError(ApplicationError):
    def __init__(self, email: str):
        super().__init__(
            message=f"An account with the email '{email}' already exists.",
            code="user_already_exists",
            status_code=409,  # 409 Conflict
        )


class InvalidCredentialsError(ApplicationError):
    def __init__(self, email: str):
        super().__init__(
            message="Authentication Failed with invalid credential.",
            code="Invalid_credentials.",
            status_code=401,
        )


class UnverifiedAccountError(ApplicationError):
    def __init__(self, email: str):
        super().__init__(
            message="User didn't varified.", code="Unvarified_user.", status_code=403
        )


class InvalidVarifyTypError(ApplicationError):
    def __init__(self, token_type):
        super().__init__(
            message=f"Invalid verification type: {token_type}.",
            code="invalid_varification_type",
            status_code=400,
        )


class UserNotFoundError(ApplicationError):
    def __init__(self, email: str):
        super().__init__(
            message=f"No user found with email {email}.",
            code="user_not_found",
            status_code=404,  # Now we can define specific HTTP codes!
        )


class UserAlreadyVerifiedError(ApplicationError):
    def __init__(self):
        super().__init__(
            "This account is already verified. Please log in.", status_code=400
        )


# --- Verification/Token Exceptions ---


class InvalidTokenError(ApplicationError):
    def __init__(self):
        super().__init__("This verification token is invalid.", status_code=400)


class TokenExpiredError(ApplicationError):
    def __init__(self):
        super().__init__(
            "This verification code has expired. Please request a new one.",
            status_code=400,
        )


class MaxVerificationAttemptsError(ApplicationError):
    def __init__(self):
        super().__init__(
            "Too many failed attempts. Please request a new code.", status_code=429
        )


class NotFoundError(ApplicationError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message, code="not_found", status_code=status.HTTP_404_NOT_FOUND
        )


class ValidationError(ApplicationError):
    """Business logic validation error."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class PermissionDeniedError(ApplicationError):
    """Permission denied for operation."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            code="permission_denied",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictError(ApplicationError):
    """Resource conflict (e.g., duplicate, has dependencies)."""

    def __init__(self, message: str):
        super().__init__(
            message=message, code="conflict", status_code=status.HTTP_409_CONFLICT
        )
