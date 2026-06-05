# rbac/conf.py

# Permissions for individual Companies/Tenants
TENANT_ROLE_BLUEPRINTS = {

    "Owner": {
        "description": (
            "Full access to all company features."
        ),
        "patterns": [
            "tenant.*",
        ],
    },

    "Admin": {
        "description": (
            "Administrative access to company operations."
        ),
        "patterns": [

            "tenant.company.view",
            "tenant.company.update",

            "tenant.employee.*",

            "tenant.department.*",

            "tenant.project.*",

            "tenant.role.view",

            "tenant.subscription.view",

            # Meetings
            "tenant.meeting.*",

            # Attendance
            "tenant.attendance.*",
        ],
    },

    "Manager": {
        "description": (
            "Department and operational management."
        ),
        "patterns": [

            "tenant.company.view",

            "tenant.employee.view",

            "tenant.department.view",

            "tenant.project.view",

            "tenant.meeting.create",
            "tenant.meeting.view",
            "tenant.meeting.update",
            "tenant.meeting.start",
            "tenant.meeting.join",
            "tenant.meeting.invite",

            "tenant.attendance.view",
        ],
    },

    "Member": {
        "description": (
            "Basic operational access."
        ),
        "patterns": [

            "tenant.company.view",

            "tenant.project.view",

            "tenant.meeting.view",
            "tenant.meeting.join",
        ],
    },
}

# Permissions for your internal Platform Staff
PLATFORM_ROLE_BLUEPRINTS = {}

later_will_add_platform = {
    "Super Admin": {
        "description": "Full platform control.",
        "patterns": ["platform.*", "tenant.company.view"],
    },
    "Support": {
        "description": "View-only access for troubleshooting.",
        "patterns": [
            "platform.tenant.view",
            "platform.tenant_user.view",
            "platform.billing.view_all",
        ],
    },
}
