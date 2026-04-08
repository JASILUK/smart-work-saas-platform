# users/selectors.py
from typing import Optional

from apps.users.models import MFADevice, User, VerificationToken


def get_user_by_email(email: str) -> Optional[User]:
    """
    Fetches a user by their email address.
    Returns None if the user does not exist.
    """
    return User.objects.filter(email=email).first()


def get_user_by_username(username: str) -> Optional[User]:
    """
    Fetches a user by their username.
    Returns None if the user does not exist.
    """
    return User.objects.filter(username=username).first()


def get_latest_unused_token(user: User, token_type: str) -> Optional[VerificationToken]:
    """
    Fetches the most recently created, unused verification token
    for a specific user and specific token type.
    """
    return (
        VerificationToken.objects.filter(
            user=user, token_type=token_type, is_used=False
        )
        .order_by("-created_at")
        .first()
    )


def get_user_by_id(user_id: int) -> Optional[User]:
    """Fetches a user by their primary key."""
    return User.objects.filter(id=user_id).first()


def user_has_mfa_enabled(user):

    return MFADevice.objects.filter(
        user=user, is_verified=True, is_active=True
    ).exists()


def get_user_mfa_devices(user):

    return MFADevice.objects.filter(user=user, is_verified=True, is_active=True)


def get_mfa_device(user, device_id):

    return MFADevice.objects.filter(id=device_id, user=user).first()
