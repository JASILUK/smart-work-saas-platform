from django.contrib import admin

from apps.meetings.models.meeting import Meeting
from apps.meetings.models.participant import MeetingParticipant
from apps.meetings.models.session import MeetingSession

# Register your models here.

admin.site.register(Meeting)
admin.site.register(MeetingParticipant)
admin.site.register(MeetingSession)