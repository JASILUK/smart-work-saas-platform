import fnmatch

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core_platform.models import PlatformRole
from apps.rbac.conf import PLATFORM_ROLE_BLUEPRINTS, TENANT_ROLE_BLUEPRINTS
from apps.rbac.models import Permission, Role

PERMISSIONS = [
    # =========================================================
    # TENANT PERMISSIONS
    # =========================================================
    # Company
    (
        "tenant.company.view",
        "View Company",
        "View company details",
        "Company",
        "tenant",
    ),
    (
        "tenant.company.update",
        "Update Company",
        "Update company info",
        "Company",
        "tenant",
    ),
    # Employees
    (
        "tenant.employee.create",
        "Create Employee",
        "Invite or create employee",
        "Employees",
        "tenant",
    ),
    (
        "tenant.employee.view",
        "View Employee",
        "View employee info",
        "Employees",
        "tenant",
    ),
    (
        "tenant.employee.update",
        "Update Employee",
        "Edit employee info",
        "Employees",
        "tenant",
    ),
    (
        "tenant.employee.delete",
        "Delete Employee",
        "Remove employee",
        "Employees",
        "tenant",
    ),
    (
        "tenant.employee.block",
        "block and unblock Employee",
        "block and unblock employee",
        "Employees",
        "tenant",
    ),
    # RBAC
    ("tenant.role.view", "View Roles", "View all roles", "RBAC", "tenant"),
    ("tenant.role.create", "Create Role", "Create new role", "RBAC", "tenant"),
    ("tenant.role.update", "Update Role", "Edit role", "RBAC", "tenant"),
    ("tenant.role.delete", "Delete Role", "Delete role", "RBAC", "tenant"),
    (
        "tenant.department.view",
        "View department",
        "View all department",
        "department",
        "tenant",
    ),
    (
        "tenant.department.create",
        "Create department",
        "Create new department",
        "department",
        "tenant",
    ),
    (
        "tenant.department.update",
        "Update department",
        "Edit department",
        "department",
        "tenant",
    ),
    (
        "tenant.department.delete",
        "Delete department",
        "Delete department",
        "department",
        "tenant",
    ),
    (
        "tenant.permission.view",
        "View Permissions",
        "View permission list",
        "RBAC",
        "tenant",
    ),
    # Projects
    (
        "tenant.project.create",
        "Create Project",
        "Create new project",
        "Projects",
        "tenant",
    ),
    ("tenant.project.view", "View Project", "View project", "Projects", "tenant"),
    ("tenant.project.update", "Update Project", "Edit project", "Projects", "tenant"),
    ("tenant.project.delete", "Delete Project", "Delete project", "Projects", "tenant"),

    # Meating 
    (
    "tenant.meeting.create",
    "Create Meeting",
    "Create meetings",
    "Meetings",
    "tenant",
    ),

    (
        "tenant.meeting.view",
        "View Meetings",
        "View meetings",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.update",
        "Update Meeting",
        "Update meetings",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.cancel",
        "Cancel Meeting",
        "Cancel meetings",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.start",
        "Start Meeting",
        "Start meeting sessions",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.join",
        "Join Meeting",
        "Join meetings",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.invite",
        "Invite Participants",
        "Invite meeting participants",
        "Meetings",
        "tenant",
    ),

    (
        "tenant.meeting.manage",
        "Manage Meetings",
        "Full meeting management",
        "Meetings",
        "tenant",
    ),

    # Attendance
    (
    "tenant.attendance.view",
    "View Attendance",
    "View attendance records",
    "Attendance",
    "tenant",
    ),

    (
        "tenant.attendance.manage",
        "Manage Attendance",
        "Manage attendance records",
        "Attendance",
        "tenant",
    ),


    # Tenant Billing
    (
        "tenant.subscription.view",
        "View Subscription",
        "View company subscription",
        "Billing",
        "tenant",
    ),
    (
        "tenant.subscription.update",
        "Update Subscription",
        "Upgrade or downgrade plan",
        "Billing",
        "tenant",
    ),
    (
        "tenant.invoice.view",
        "View Invoices",
        "View billing invoices",
        "Billing",
        "tenant",
    ),
    (
        "tenant.billing.update",
        "Update Billing Info",
        "Update billing details",
        "Billing",
        "tenant",
    ),
    # =========================================================
    # PLATFORM PERMISSIONS
    # =========================================================
    # Tenants
    (
        "platform.tenant.create",
        "Create Tenant",
        "Create new tenant/company",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant.view",
        "View Tenants",
        "View tenant list and details",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant.update",
        "Update Tenant",
        "Update tenant information",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant.suspend",
        "Suspend Tenant",
        "Suspend tenant account",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant.activate",
        "Activate Tenant",
        "Activate suspended tenant",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant.delete",
        "Delete Tenant",
        "Delete tenant account",
        "Tenants",
        "platform",
    ),
    # Tenant Users
    (
        "platform.tenant_user.view",
        "View Tenant Users",
        "View users inside tenants",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant_user.update",
        "Update Tenant User",
        "Edit tenant user",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant_user.disable",
        "Disable Tenant User",
        "Disable tenant user account",
        "Tenants",
        "platform",
    ),
    (
        "platform.tenant_user.enable",
        "Enable Tenant User",
        "Enable tenant user account",
        "Tenants",
        "platform",
    ),
    # Subscription management
    (
        "platform.subscription.view_all",
        "View All Subscriptions",
        "View all tenant subscriptions",
        "Subscriptions",
        "platform",
    ),
    (
        "platform.subscription.update",
        "Update Subscription",
        "Modify tenant subscription",
        "Subscriptions",
        "platform",
    ),
    # Billing
    (
        "platform.billing.view_all",
        "View Billing Records",
        "View all billing transactions",
        "Billing",
        "platform",
    ),
    (
        "platform.billing.refund",
        "Refund Payment",
        "Issue payment refund",
        "Billing",
        "platform",
    ),
    # Plans
    (
        "platform.plan.create",
        "Create Plan",
        "Create subscription plan",
        "Plans",
        "platform",
    ),
    (
        "platform.plan.view",
        "View Plans",
        "View subscription plans",
        "Plans",
        "platform",
    ),
    (
        "platform.plan.update",
        "Update Plan",
        "Update subscription plan",
        "Plans",
        "platform",
    ),
    (
        "platform.plan.delete",
        "Delete Plan",
        "Delete subscription plan",
        "Plans",
        "platform",
    ),
    # Platform Users
    (
        "platform.user.create",
        "Create Platform User",
        "Create internal admin user",
        "Platform Users",
        "platform",
    ),
    (
        "platform.user.view",
        "View Platform Users",
        "View platform admin users",
        "Platform Users",
        "platform",
    ),
    (
        "platform.user.update",
        "Update Platform User",
        "Edit platform admin user",
        "Platform Users",
        "platform",
    ),
    (
        "platform.user.delete",
        "Delete Platform User",
        "Delete platform admin user",
        "Platform Users",
        "platform",
    ),
    # RBAC (platform)
    (
        "platform.permission.view",
        "View Permissions",
        "View system permissions",
        "RBAC",
        "platform",
    ),
    (
        "platform.permission.create",
        "Create Permission",
        "Create system permission",
        "RBAC",
        "platform",
    ),
    (
        "platform.permission.update",
        "Update Permission",
        "Update system permission",
        "RBAC",
        "platform",
    ),
    (
        "platform.permission.delete",
        "Delete Permission",
        "Delete system permission",
        "RBAC",
        "platform",
    ),
    (
        "platform.role.create",
        "Create Platform Role",
        "Create platform role",
        "RBAC",
        "platform",
    ),
    (
        "platform.role.view",
        "View Platform Roles",
        "View platform roles",
        "RBAC",
        "platform",
    ),
    (
        "platform.role.update",
        "Update Platform Role",
        "Update platform role",
        "RBAC",
        "platform",
    ),
    (
        "platform.role.delete",
        "Delete Platform Role",
        "Delete platform role",
        "RBAC",
        "platform",
    ),
    # System
    (
        "platform.system.settings",
        "Manage System Settings",
        "Manage platform configuration",
        "System",
        "platform",
    ),
    (
        "platform.system.audit_logs",
        "View Audit Logs",
        "View platform audit logs",
        "System",
        "platform",
    ),
]


# =========================================================
# 3. THE COMMAND
# =========================================================
class Command(BaseCommand):
    help = "One-stop sync for permissions and all role types."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Starting System Sync ---"))

        # 1. Update Permission Table
        all_perms = self._seed_permissions()

        # 2. Update Platform Roles (Internal Staff)
        self._sync_generic_roles(PlatformRole, PLATFORM_ROLE_BLUEPRINTS, all_perms)

        # 3. Update Tenant Roles (All Companies)
        # This finds every "Admin" in every company and updates them
        self._sync_generic_roles(Role, TENANT_ROLE_BLUEPRINTS, all_perms)

        self.stdout.write(self.style.SUCCESS("✅ System is fully up to date."))

    def _seed_permissions(self):
        for code, name, desc, cat, scope in PERMISSIONS:
            Permission.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "category": cat,
                    "scope": scope,
                },
            )
        return list(Permission.objects.all())

    def _sync_generic_roles(self, model_class, blueprint, all_perms):
        for role_name, config in blueprint.items():
            # Update all roles matching this name (e.g., all "Admin" roles)
            # For Tenant Roles, this filters across ALL companies
            target_roles = model_class.objects.filter(name=role_name)

            # If no roles exist (first run), create one default
            if not target_roles.exists() and model_class == PlatformRole:
                role, _ = model_class.objects.get_or_create(name=role_name)
                target_roles = [role]

            patterns = config.get("patterns", [])
            matches = [
                p
                for p in all_perms
                if any(fnmatch.fnmatch(p.code, pat) for pat in patterns)
            ]

            for r in target_roles:
                r.permissions.set(matches)

        self.stdout.write(
            f"Synced {model_class.__name__} for: {list(blueprint.keys())}"
        )
