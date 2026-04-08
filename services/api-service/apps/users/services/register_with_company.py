# users/services/register_with_company_service.py

from django.db import transaction

from apps.companies.services.company_service import CompanyService
from apps.core.exceptions import UserAlreadyExistsError
from apps.users.models import User, VerificationToken
from apps.users.selectors import get_user_by_email
from apps.users.services.verification import VerificationService


class RegisterUserWithCompanyService:

    def __init__(self):
        self.verification_service = VerificationService()
        self.company_service = CompanyService()

    @transaction.atomic
    def execute(self, *, email, password, username, company_name):

        user = get_user_by_email(email=email)

        if user and user.is_verified:
            raise UserAlreadyExistsError(email=email)

        if not user:
            user = User.objects.create_user(
                email=email,
                password=password,
                username=username,
                is_verified=False,
            )
        else:
            user.username = username
            user.set_password(password)
            user.save()

        # Create pending company
        self.company_service.create_pending_company(owner=user, name=company_name)

        # Send OTP
        self.verification_service.send(
            user=user,
            token_type=VerificationToken.TokenType.EMAIL_VERIFY,
            mode="OTP",
            channel="EMAIL",
        )

        return user
