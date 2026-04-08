import base64
import secrets
from io import BytesIO

import pyotp
import qrcode
from django.core.signing import BadSignature, TimestampSigner

from apps.core.exceptions import ApplicationError, InvalidTokenError
from apps.users.selectors import get_mfa_device, get_user_by_id

signer = TimestampSigner()


from apps.users.models import BackupCode, MFADevice


class MFASetupService:

    def __init__(self, user):
        self.user = user

    def execute(self, device_name):

        secret = pyotp.random_base32()

        device = MFADevice.objects.create(
            user=self.user,
            name=device_name,
            secret=secret,
            is_verified=False,
        )

        totp = pyotp.TOTP(secret)

        uri = totp.provisioning_uri(name=self.user.email, issuer_name="SBMS")

        qr = qrcode.make(uri)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return {"device_id": device.id, "qr_code": qr_base64}


class MFAVerifyService:

    def __init__(self, user, device_id, code):
        self.user = user
        self.device_id = device_id
        self.code = code.replace("-", "").lower().strip()

    def verify(self):

        device = get_mfa_device(self.user, self.device_id)

        if not device:
            raise ApplicationError("Invalid device")

        totp = pyotp.TOTP(device.secret)

        if not totp.verify(self.code):
            raise ApplicationError(message="Invalid code")

        device.is_verified = True
        device.save(update_fields=["is_verified"])

        backup_codes = BackupCodeService(self.user).generate()

        return backup_codes


class MFALoginVerifyService:

    def __init__(self, user, device_id, code):
        self.user = user
        self.device_id = device_id
        self.code = code.strip()

    def verify(self):

        device_id = None if self.device_id in [None, "", "null"] else self.device_id

        # ---- TOTP verification ----
        if device_id:

            device = get_mfa_device(self.user, device_id)

            if device:
                totp = pyotp.TOTP(device.secret)

                if totp.verify(self.code):
                    return True

        # ---- Backup code verification ----
        backup = BackupCode.objects.filter(
            user=self.user, code=self.code, used=False
        ).first()

        if backup:
            backup.used = True
            backup.save(update_fields=["used"])
            return True

        raise ApplicationError(message="Invalid verification code")


class TempTokenService:

    @staticmethod
    def create(user):
        value = f"user:{user.id}"
        return signer.sign(value)

    @staticmethod
    def decode_and_user(token):

        if not token:
            raise InvalidTokenError()

        try:
            value = signer.unsign(token, max_age=300)

            user_id = value.split(":")[1]

            user = get_user_by_id(user_id=int(user_id))

            if not user:
                raise ApplicationError(message="User not found")

            return user

        except BadSignature:
            raise InvalidTokenError()


class BackupCodeService:

    def __init__(self, user):
        self.user = user

    def generate(self):

        codes = []

        for _ in range(10):

            code = secrets.token_hex(4)

            BackupCode.objects.create(user=self.user, code=code)

            codes.append(code)

        return codes

    def regenerate_codes(self):

        # ensure MFA enabled
        device_exists = MFADevice.objects.filter(
            user=self.user, is_verified=True, is_active=True
        ).exists()

        if not device_exists:
            raise ApplicationError(message="Enable MFA before generating backup codes")

        # delete old codes
        BackupCode.objects.filter(user=self.user).delete()

        return self.generate()
