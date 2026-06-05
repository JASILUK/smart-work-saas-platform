from django.contrib import admin

from apps.reminders.models.reminder import Reminder

# Register your models here.
admin.site.register(Reminder)