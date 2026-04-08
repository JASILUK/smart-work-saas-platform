from django.db import models

from apps.core.models import TimeStampedModel


class PlatformRole(models.Model):

    name = models.CharField(max_length=100)

    permissions = models.ManyToManyField(
        "rbac.Permission", related_name="platform_roles", blank=True
    )

    def __str__(self):
        return self.name


class PlatformProfile(TimeStampedModel):

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="platform_profile"
    )

    role = models.ForeignKey(PlatformRole, on_delete=models.PROTECT)

    is_active = models.BooleanField(default=True)
