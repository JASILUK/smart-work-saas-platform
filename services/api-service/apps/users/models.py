from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.users.managers import CustomUserManager


# ==========================================
# 1. CORE IDENTITY & SECURITY
# ==========================================
class User(AbstractUser, TimeStampedModel):
    """The master identity. Strictly for login logic and global flags."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)

    # Phone Verification System
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)

    # Global email/account verification flag
    is_verified = models.BooleanField(default=False)
    active_company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_users",
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class MFADevice(TimeStampedModel):

    class DeviceType(models.TextChoices):
        TOTP = "totp", "Authenticator App"
        SMS = "sms", "SMS OTP"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mfa_devices")

    name = models.CharField(max_length=100)

    device_type = models.CharField(max_length=20, choices=DeviceType.choices)

    secret = models.CharField(max_length=255)

    is_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    last_used_at = models.DateTimeField(null=True, blank=True)


class BackupCode(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    code = models.CharField(max_length=20)

    used = models.BooleanField(default=False)


class SocialAccount(TimeStampedModel):

    class ProviderChoices(models.TextChoices):
        GOOGLE = "google", "Google"
        GITHUB = "github", "GitHub"
        APPLE = "apple", "Apple"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_accounts"
    )

    provider = models.CharField(max_length=20, choices=ProviderChoices.choices)

    provider_account_id = models.CharField(max_length=255)

    email = models.EmailField()

    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("provider", "provider_account_id")


class VerificationToken(TimeStampedModel):
    """Pluggable system for OTPs and Magic Links."""

    class TokenType(models.TextChoices):
        EMAIL_VERIFY = "EMAIL_VERIFY"
        PASSWORD_RESET = "PASSWORD_RESET"
        INVITE = "INVITE"
        TWO_FACTOR = "TWO_FACTOR"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_tokens"
    )
    token_type = models.CharField(max_length=20, choices=TokenType.choices)
    token = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


# # ==========================================
# # 2. PROFILES (Global)
# # ==========================================
# class GlobalProfile(TimeStampedModel):
#     """Data true everywhere across the internet."""
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='global_profile')
#     full_name = models.CharField(max_length=255, blank=True)
#     avatar_url = models.URLField(blank=True, null=True)
#     timezone = models.CharField(max_length=50, default='UTC')
