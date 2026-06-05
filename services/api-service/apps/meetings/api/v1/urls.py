from django.urls import path

from apps.meetings.api.v1.views.meeting_views import MeetingDetailAPI, MeetingListCreateAPI, MeetingTargetDetailAPI, MeetingTargetListCreateAPI
from apps.meetings.api.v1.views.participants_views import MeetingParticipantDetailAPI, MeetingParticipantListCreateAPI
from apps.meetings.api.v1.views.session_view import EndMeetingSessionAPI, JoinMeetingSessionAPI, LeaveMeetingSessionAPI, MeetingSessionDetailAPI, StartMeetingSessionAPI

urlpatterns = [
    # =====================================================
    # MEETINGS
    # =====================================================

    path(
        "",
        MeetingListCreateAPI.as_view(),
        name="meeting-list-create",
    ),

    path(
        "<uuid:public_id>/",
        MeetingDetailAPI.as_view(),
    ),

    path(
        "<uuid:public_id>/targets/",
        MeetingTargetListCreateAPI.as_view(),
    ),

    path(
        "<uuid:public_id>/targets/<int:target_id>/",
        MeetingTargetDetailAPI.as_view(),
    ),


    path(
        "<uuid:public_id>/participants/",
        MeetingParticipantListCreateAPI.as_view(),
        name="meeting-participant-list-create",
    ),

    path(
        (
            "<uuid:public_id>/participants/"
            "<int:participant_id>/"
        ),
        MeetingParticipantDetailAPI.as_view(),
        name="meeting-participant-detail",
    ),

    path(
        "<uuid:public_id>/session/",
        MeetingSessionDetailAPI.as_view(),
        name="meeting-participant-list-create",
    ),

    path( "<uuid:public_id>/session/start/" ,
        StartMeetingSessionAPI.as_view(),
        name="meeting-participant-detail",
    ),

    path( "<uuid:public_id>/session/end/" ,
        EndMeetingSessionAPI.as_view(),
        name="meeting-participant-detail",
    ),

    path( "<uuid:public_id>/session/join/" ,
        JoinMeetingSessionAPI.as_view(),
        name="meeting-participant-detail",
    ),

    path( "<uuid:public_id>/session/leave/" ,
        LeaveMeetingSessionAPI.as_view(),
        name="meeting-participant-detail",
    ),
]