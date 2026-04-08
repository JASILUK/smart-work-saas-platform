# rbac/conf.py

# Permissions for individual Companies/Tenants
TENANT_ROLE_BLUEPRINTS = {
    "Owner": {
        "description": "Full access to all company features.",
        "patterns": ["tenant.*"],
    },
    "Admin": {
        "description": "Management access excluding sensitive company-wide destructive actions.",
        "patterns": [
            "tenant.company.view",
            "tenant.employee.*",
            "tenant.department.*",
            "tenant.project.*",
            "tenant.role.view",
            "tenant.subscription.view",
        ],
    },
    "Member": {
        "description": "Basic operational access.",
        "patterns": [
            "tenant.company.view",
            "tenant.project.view",
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
