from django.contrib import admin

# Register your models here.
from apps.attendance.models.holiday import Holiday

admin.site.register(Holiday)