# companies/services/invite_service.py

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from apps.companies.models import CompanyInvite, Membership
from apps.companies.tasks.invite_tasks import send_invite_email_task
from apps.core.exceptions import ApplicationError, InvalidCredentialsError
from apps.users.selectors import get_user_by_email
from apps.users.services.notification import NotificationService
from apps.users.services.registration import UserRegistrationService


class CompanyInviteService:

    EXPIRY_HOURS = 48

    def __init__(self):
        self.user_service = UserRegistrationService()
        self.notification_service = NotificationService()

    # ----------------------------------
    # PREPARE INVITE OBJECT
    # ----------------------------------
    def prepare_invite(self, *, company, inviter, email, role, department=None):

        raw_secret = secrets.token_urlsafe(32)

        invite = CompanyInvite(
            company=company,
            invited_by=inviter,
            email=email,
            role=role,
            department=department,
            token_hash=make_password(raw_secret),
            expires_at=timezone.now() + timedelta(hours=self.EXPIRY_HOURS),
        )

        return invite, raw_secret

    # ----------------------------------
    # SINGLE INVITE
    # ----------------------------------
    @transaction.atomic
    def create_invite(self, *, company, inviter, email, role, department=None):

        # Invalidate previous active invites
        CompanyInvite.objects.filter(
            company=company, email=email, is_used=False
        ).update(is_used=True)

        invite, raw_secret = self.prepare_invite(
            company=company,
            inviter=inviter,
            email=email,
            role=role,
            department=department,
        )

        invite.save()

        # Send email AFTER commit
        def enqueue_email():
            send_invite_email_task.delay(invite.id, raw_secret)

        # def send_email():

        #     self.send_invite_email(invite=invite, raw_secret=raw_secret)

        transaction.on_commit(enqueue_email)

        return invite

    # ----------------------------------
    # EMAIL SENDER
    # ----------------------------------
    def send_invite_email(self, *, invite, raw_secret):

        invite_link = (
            f"{settings.FRONTEND_URL}/invite" f"?token={invite.token_id}.{raw_secret}"
        )

        context = {
            "company_name": invite.company.name,
            "invite_link": invite_link,
            "expiry_hours": self.EXPIRY_HOURS,
        }

        self.notification_service.send_notification(
            channel="EMAIL",
            recipient=invite.email,
            template_name="company_invite",
            context=context,
            subject=f"You are invited to join {invite.company.name}",
        )

    # ----------------------------------
    # VALIDATE INVITE
    # ----------------------------------
    def validate_invite(self, *, full_token):

        try:
            token_id, raw_secret = full_token.split(".")
        except ValueError:
            raise Exception("Invalid token format")

        invite = (
            CompanyInvite.objects.select_related(
                "company", "invited_by", "role", "department"
            )
            .filter(token_id=token_id, is_used=False)
            .first()
        )

        if not invite:
            raise Exception("Invalid invite")

        if invite.is_expired():
            raise Exception("Invite expired")

        if not check_password(raw_secret, invite.token_hash):
            raise Exception("Invalid token")

        user_exists = get_user_by_email(email=invite.email)

        return invite, user_exists

    # ----------------------------------
    # ACCEPT INVITE
    # ----------------------------------
    @transaction.atomic
    def accept_invite(
        self, *, full_token, request_user=None, password=None, username=None
    ):

        invite, existing_user = self.validate_invite(full_token=full_token)

        if request_user and request_user.is_authenticated:
            if request_user.email != invite.email:
                raise ApplicationError(message="Invite not for this user")
            user = request_user

        elif existing_user:
            user = existing_user

        else:
            if not password or not username:
                raise ApplicationError(message="Password and username required")

            user = self.user_service.create_invited_user(
                email=invite.email, password=password, username=username
            )

        membership, created = Membership.objects.get_or_create(
            user=user,
            company=invite.company,
            defaults={"role": invite.role, "department": invite.department},
        )

        # ✅ INTEGRATION: Provision active policy allocations for the employee profile
        from apps.attendance.services.leave_provisioning_service import LeaveBalanceProvisioningService
        LeaveBalanceProvisioningService.provision_for_membership(membership=membership)

        invite.is_used = True
        invite.save(update_fields=["is_used"])

        return user, invite.company
