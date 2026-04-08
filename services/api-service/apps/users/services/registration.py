from django.db import transaction

from apps.companies.services.company_activation_service import CompanyActivationService
from apps.core.exceptions import ApplicationError, UserAlreadyExistsError, UserNotFoundError
from apps.users.models import User, VerificationToken
from apps.users.selectors import get_user_by_email
from apps.users.services.auth_service import AuthService
from apps.users.services.notification import NotificationService
from apps.users.tasks.notification_tasks import send_notification_task

from .verification import VerificationService


class UserRegistrationService:
    def __init__(self):
        self.verification_service = VerificationService()
        self.notification_service = NotificationService()  # FIXED: Added this!
        self.activate_company_service = CompanyActivationService()
        self.auth_service = AuthService()

    def register_user(self, email: str, password: str, username: str) -> User:
        """
        The main public method to register a user.
        No @transaction.atomic here, to protect the database from slow email APIs.
        """
        user = get_user_by_email(email=email)

        if user:
            if user.is_verified:
                raise UserAlreadyExistsError(email=email)

            # Update the unverified user
            user.username = username
            user.set_password(password)
            user.save()

        else:
            # FIXED: Removed dead code and handled creation cleanly
            user = User.objects.create_user(
                email=email, username=username, password=password, is_verified=False
            )

        # Delegate verification to the sub-service
        self.verification_service.send(
            user=user,
            token_type=VerificationToken.TokenType.EMAIL_VERIFY,
            mode="OTP",
            channel="EMAIL",
        )

        return user

    def complete_registration(self, email: str, token: str):
        """Called when the user types the OTP."""
        # 1. Ask the dumb service to verify the token

        user = get_user_by_email(email)
        self.verification_service.verify(
            user=user,
            token_type=VerificationToken.TokenType.EMAIL_VERIFY,
            raw_token=token,
        )

        if user.is_verified:
            raise ApplicationError("User is already verified.")

        # 2. Mark as verified
        user.is_verified = True
        user.save()

        self.activate_company_service.activate_for_verified_user(user=user)

        payload = self.auth_service.login_after_verification(user=user)

        # 3. Send the specific welcome notification
        send_notification_task.delay(
            channel="EMAIL",
            recipient=user.email,
            subject="Welcome to our SaaS!",
            content="Your account is fully verified.",
        )
        # self.notification_service.send_notification(
        #     channel="EMAIL",
        #     recipient=user.email,
        #     subject="Welcome to our SaaS!",
        #     content="Your account is fully verified.",
        # )
        return payload

    def resend_verification_email(self, email: str):
        """
        Triggers a fresh OTP for a user who hasn't verified yet.
        """

        user = get_user_by_email(email)

        if not user:
            raise UserNotFoundError(email)

        if user.is_verified:
            raise UserAlreadyExistsError(email=email)

        self.verification_service.send(
            user=user,
            token_type=VerificationToken.TokenType.EMAIL_VERIFY,
            mode="OTP",
            channel="EMAIL",
        )

    def create_invited_user(self, *, email, password, username):

        user = User.objects.create_user(
            email=email, password=password, is_verified=True, username=username
        )

        return user
