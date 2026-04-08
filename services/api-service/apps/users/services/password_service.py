from django.contrib.auth.hashers import check_password

from apps.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from apps.users.models import User, VerificationToken
from apps.users.selectors import get_user_by_email
from apps.users.services.verification import VerificationService


class PasswordService:

    def __init__(self):
        self.verification_service = VerificationService()

    def request_reset(self, email):

        user = get_user_by_email(email=email)

        if not user:
            # ⚠️ Important:
            # Do NOT reveal if user exists (security)
            return

        self.verification_service.send(
            user=user,
            token_type=VerificationToken.TokenType.PASSWORD_RESET,
            mode="LINK",  # or LINK if you prefer
            channel="EMAIL",
        )

    def reset_password(self, email, token, new_password):

        user = User.objects.filter(email=email).first()

        if not user:
            raise InvalidTokenError()

        # Verify token
        self.verification_service.verify(
            user=user,
            token_type=VerificationToken.TokenType.PASSWORD_RESET,
            raw_token=token,
        )

        # Update password
        user.set_password(new_password)
        user.save()

        return True

    def change_password(self, user, current_password, new_password):

        if not check_password(current_password, user.password):
            raise InvalidCredentialsError()

        user.set_password(new_password)
        user.save()

        return True
