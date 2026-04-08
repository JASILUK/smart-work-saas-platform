from django.contrib import admin

from apps.rbac.models import Permission, Role

# Register your models here.
admin.site.register(Permission)
admin.site.register(Role)
