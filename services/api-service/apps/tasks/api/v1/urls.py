from django.urls import path

from apps.tasks.api.v1.views.task_views import (
    TaskListCreateAPIView,
    MyTasksAPIView,
    TeamTasksAPIView,
    TaskDetailAPIView,
    TaskAssignAPIView,
    TaskStatusAPIView,
    ProjectTaskListAPIView,
    ProjectTaskSummaryAPIView,
)

app_name = "tasks"

urlpatterns = [

    # ==========================================================
    # Task CRUD
    # ==========================================================

    path(
        "",
        TaskListCreateAPIView.as_view(),
        name="task-create",
    ),

    path(
        "my/",
        MyTasksAPIView.as_view(),
        name="my-tasks",
    ),

    path(
        "team/",
        TeamTasksAPIView.as_view(),
        name="team-tasks",
    ),

    path(
        "<int:task_id>/",
        TaskDetailAPIView.as_view(),
        name="task-detail",
    ),



    # ==========================================================
    # Task Actions
    # ==========================================================

    path(
        "<int:task_id>/assign/",
        TaskAssignAPIView.as_view(),
        name="task-assign",
    ),

    path(
        "<int:task_id>/status/",
        TaskStatusAPIView.as_view(),
        name="task-status",
    ),

    # ==========================================================
    # Project Task APIs
    # ==========================================================

    path(
        "projects/<int:project_id>/",
        ProjectTaskListAPIView.as_view(),
        name="project-task-list",
    ),

    path(
        "projects/<int:project_id>/summary/",
        ProjectTaskSummaryAPIView.as_view(),
        name="project-task-summary",
    ),
]