# companies/services/bulk_invite_service.py

import csv
from io import TextIOWrapper

from django.db import transaction

from apps.companies.models import CompanyInvite, Department
from apps.companies.services.invite_service import CompanyInviteService
from apps.companies.tasks.invite_tasks import send_invite_email_task
from apps.rbac.models import Role


class BulkInviteService:

    def __init__(self):
        self.invite_service = CompanyInviteService()

    # ----------------------------------
    # JSON BULK
    # ----------------------------------
    @transaction.atomic
    def process(self, *, company, inviter, invite_items):

        unique = {item["email"].lower(): item for item in invite_items}

        invite_objects = []
        secrets_map = {}
        failed = []

        for item in unique.values():
            try:
                invite, raw_secret = self.invite_service.prepare_invite(
                    company=company,
                    inviter=inviter,
                    email=item["email"],
                    role=item["role"],
                    department=item.get("department"),
                )

                invite_objects.append(invite)
                secrets_map[item["email"]] = raw_secret

            except Exception as e:
                failed.append({"email": item["email"], "error": str(e)})

        if not invite_objects:
            return {"created_count": 0, "failed_count": len(failed), "failed": failed}

        emails = [obj.email for obj in invite_objects]

        CompanyInvite.objects.filter(
            company=company, email__in=emails, is_used=False
        ).update(is_used=True)

        created_invites = CompanyInvite.objects.bulk_create(invite_objects)

        def enqueue_notifications():
            for invite in created_invites:
                raw_secret = secrets_map.get(invite.email)

                send_invite_email_task.delay(invite.id, raw_secret)

        # def send_notifications():
        #     for invite in created_invites:
        #         raw_secret = secrets_map.get(invite.email)
        #         self.invite_service.send_invite_email(
        #             invite=invite, raw_secret=raw_secret
        #         )

        transaction.on_commit(enqueue_notifications)

        return {
            "created_count": len(created_invites),
            "failed_count": len(failed),
            "failed": failed,
        }

    # ----------------------------------
    # CSV BULK
    # ----------------------------------
    def process_csv(self, *, company, inviter, file):
        decoded = TextIOWrapper(file, encoding="utf-8")
        reader = csv.DictReader(decoded)
        rows = list(reader)

        # 1. Collect all roles and departments belonging to this company FIRST
        # Don't filter by CSV names yet to avoid case-sensitive issues in SQL
        all_roles = Role.objects.filter(company=company)
        all_depts = Department.objects.filter(company=company)

        # 2. Build Case-Insensitive Maps (Key is lowercase)
        roles_map = {r.name.lower(): r for r in all_roles}
        depts_map = {d.name.lower(): d for d in all_depts}

        invite_items = []
        failed = []

        for row in rows:
            try:
                email = (row.get("email") or "").strip().lower()
                if not email:
                    raise ValueError("Email is required")

                # Handle Role
                role_input = (row.get("role") or "").strip()
                role = roles_map.get(role_input.lower())

                if not role:
                    # This will now show the actual roles available in the DB
                    valid_options = ", ".join([r.name for r in all_roles])
                    raise ValueError(
                        f"Role '{role_input}' not found. Available: {valid_options}"
                    )

                # Handle Department
                dept_input = (row.get("department") or "").strip()
                department = depts_map.get(dept_input.lower()) if dept_input else None

                # If they provided a dept name but it doesn't exist
                if dept_input and not department:
                    valid_depts = ", ".join([d.name for d in all_depts])
                    raise ValueError(
                        f"Dept '{dept_input}' not found. Available: {valid_depts}"
                    )

                invite_items.append(
                    {"email": email, "role": role, "department": department}
                )

            except Exception as e:
                failed.append({"email": row.get("email"), "error": str(e)})

        # 3. Call the atomic process method
        result = self.process(
            company=company, inviter=inviter, invite_items=invite_items
        )

        result["failed"].extend(failed)
        result["failed_count"] += len(failed)
        return result
