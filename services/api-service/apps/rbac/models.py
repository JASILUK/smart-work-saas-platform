from django.db import models

from apps.core.models import TimeStampedModel


class Permission(TimeStampedModel):

    SCOPE_CHOICES = (
        ("platform", "Platform"),
        ("tenant", "Tenant"),
    )

    code = models.CharField(max_length=100, unique=True)

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    category = models.CharField(max_length=100)

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="tenant")

    def __str__(self):
        return self.code


class Role(TimeStampedModel):

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="roles"
    )

    name = models.CharField(max_length=100)

    is_system_role = models.BooleanField(default=False)

    permissions = models.ManyToManyField(
        "rbac.Permission", blank=True, related_name="roles"
    )

    def __str__(self):
        return f"{self.company.name} - {self.name}"
