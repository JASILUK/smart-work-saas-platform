from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.exceptions import NotFound

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    PaginationAdapter,
    StandardLimitOffsetPagination,
)
from apps.tasks.api.v1.serializers.task_serializers import (
    ProjectTaskSummarySerializer,
    TaskAssignSerializer,
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskStatusSerializer,
    TaskUpdateSerializer,
)
from apps.tasks.models.tasks import Task, TaskPriority, TaskStatus
from apps.tasks.selectors.task_selector import TaskSelector
from apps.tasks.services.task_service import TaskService


# =============================================================================
# PRIVATE VIEW HELPERS
# =============================================================================

def _extract_task_query_params(request) -> Dict[str, Any]:
    """
    Extract and sanitize common task query filter parameters from request.
    """
    project_id = request.query_params.get("project_id")
    assigned_to_id = request.query_params.get("assigned_to_id")
    created_by_id = request.query_params.get("created_by_id")
    department_id = request.query_params.get("department_id")

    return {
        "search": request.query_params.get("search"),
        "status": request.query_params.get("status"),
        "priority": request.query_params.get("priority"),
        "project_id": int(project_id) if project_id and project_id.isdigit() else None,
        "assigned_to_id": int(assigned_to_id) if assigned_to_id and assigned_to_id.isdigit() else None,
        "created_by_id": int(created_by_id) if created_by_id and created_by_id.isdigit() else None,
        "department_id": int(department_id) if department_id and department_id.isdigit() else None,
        "is_personal": _parse_bool_param(request.query_params.get("is_personal")),
        "is_overdue": _parse_bool_param(request.query_params.get("is_overdue")),
        "is_today": _parse_bool_param(request.query_params.get("is_today")),
        "is_this_week": _parse_bool_param(request.query_params.get("is_this_week")),
        "ordering": request.query_params.get("ordering", "-created_at"),
    }


def _parse_bool_param(value: Optional[str]) -> Optional[bool]:
    """
    Parse string boolean query parameters safely.
    """
    if value is None:
        return None
    val_lower = str(value).strip().lower()
    if val_lower in ("true", "1", "yes"):
        return True
    if val_lower in ("false", "0", "no"):
        return False
    return None


def _build_task_filter_options() -> Dict[str, list]:
    """
    Build structured choice definitions for frontend filter dropdowns.
    """
    return {
        "statuses": [
            {"value": choice[0], "label": choice[1]}
            for choice in TaskStatus.choices
        ],
        "priorities": [
            {"value": choice[0], "label": choice[1]}
            for choice in TaskPriority.choices
        ],
        "ordering": [
            {"value": "-created_at", "label": "Newest first"},
            {"value": "created_at", "label": "Oldest first"},
            {"value": "due_date", "label": "Due date (Ascending)"},
            {"value": "-due_date", "label": "Due date (Descending)"},
            {"value": "priority", "label": "Priority"},
            {"value": "title", "label": "Title (A-Z)"},
        ],
    }


# =============================================================================
# TASK LIST & CREATE
# =============================================================================

class TaskListCreateAPIView(BaseCompanyAPIView):
    """
    GET  /api/v1/tasks/ — Company-wide task list with filtering and metrics.
    POST /api/v1/tasks/ — Create a Personal or Project task.
    """

    def get(self, request, *args, **kwargs):
        company = request.company
        params = _extract_task_query_params(request)

        queryset = TaskSelector.get_company_tasks(
            company=company,
            **params,
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = TaskListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.get_metadata(paginator, paginated_page)
        filters = _build_task_filter_options()

        # Compute summary metrics for company dashboard
        summary = TaskSelector.get_task_metrics_summary(company=company)

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )

    def post(self, request, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = TaskService.create_task(
            company_id=company.id,
            created_by_id=membership.id,
            **serializer.validated_data,
        )

        detail_serializer = TaskDetailSerializer(task)
        return ApiResponse.success(
            data=detail_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# USER WORKSPACE TASKS ("MY TASKS")
# =============================================================================

class MyTasksAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/tasks/my/ — Personal task dashboard (Assigned to or created by requesting member).
    """

    def get(self, request, *args, **kwargs):
        company = request.company
        membership = request.membership
        params = _extract_task_query_params(request)

        # Remove arguments handled explicitly by user workspace filter
        params.pop("created_by_id", None)
        params.pop("assigned_to_id", None)

        queryset = TaskSelector.get_my_tasks(
            company=company,
            membership=membership,
            **params,
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = TaskListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.get_metadata(paginator, paginated_page)
        filters = _build_task_filter_options()

        summary = TaskSelector.get_task_metrics_summary(
            company=company,
            membership_id=membership.id,
        )

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )


# =============================================================================
# MANAGED TEAM TASKS
# =============================================================================

class TeamTasksAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/tasks/team/ — Query tasks from projects owned or managed by requesting user.
    """

    def get(self, request, *args, **kwargs):
        company = request.company
        membership = request.membership
        params = _extract_task_query_params(request)

        queryset = TaskSelector.get_managed_team_tasks(
            company=company,
            membership=membership,
            search=params.get("search"),
            status=params.get("status"),
            priority=params.get("priority"),
            project_id=params.get("project_id"),
            assigned_to_id=params.get("assigned_to_id"),
            is_overdue=params.get("is_overdue"),
            is_today=params.get("is_today"),
            ordering=params.get("ordering"),
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = TaskListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.get_metadata(paginator, paginated_page)
        filters = _build_task_filter_options()

        summary = TaskSelector.get_task_metrics_summary(
            company=company,
            is_managed_team_only=True,
            requesting_membership=membership,
        )

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )


# =============================================================================
# TASK DETAIL & GENERAL MUTATIONS
# =============================================================================

class TaskDetailAPIView(BaseCompanyAPIView):
    """
    GET    /api/v1/tasks/{id}/ — Retrieve task details.
    PATCH  /api/v1/tasks/{id}/ — Update task fields.
    DELETE /api/v1/tasks/{id}/ — Delete a task.
    """

    def get(self, request, task_id: int, *args, **kwargs):
        company = request.company

        task = TaskSelector.get_by_id(company=company, task_id=task_id)
        if not task:
            raise NotFound("Task not found.")

        serializer = TaskDetailSerializer(task)
        return ApiResponse.success(data=serializer.data)

    def patch(self, request, task_id: int, *args, **kwargs):
        company = request.company

        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_task = TaskService.update_task(
            company_id=company.id,
            task_id=task_id,
            **serializer.validated_data,
        )

        detail_serializer = TaskDetailSerializer(updated_task)
        return ApiResponse.success(data=detail_serializer.data)

    def delete(self, request, task_id: int, *args, **kwargs):
        company = request.company

        deleted_info = TaskService.delete_task(
            company_id=company.id,
            task_id=task_id,
        )

        return ApiResponse.success(
            data={
                "id": deleted_info["id"],
                "title": deleted_info["title"],
                "message": "Task deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# TASK ASSIGNMENT ACTION
# =============================================================================

class TaskAssignAPIView(BaseCompanyAPIView):
    """
    POST /api/v1/tasks/{id}/assign/ — Assign or reassign a task to an employee.
    """

    def post(self, request, task_id: int, *args, **kwargs):
        company = request.company

        serializer = TaskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_task = TaskService.assign_task(
            company_id=company.id,
            task_id=task_id,
            assigned_to_id=serializer.validated_data["assigned_to_id"],
        )

        detail_serializer = TaskDetailSerializer(updated_task)
        return ApiResponse.success(
            data={
                "task": detail_serializer.data,
                "message": "Task reassigned successfully.",
            }
        )


# =============================================================================
# TASK STATUS CHANGE ACTION
# =============================================================================

class TaskStatusAPIView(BaseCompanyAPIView):
    """
    POST /api/v1/tasks/{id}/status/ — Transition task status.
    """

    def post(self, request, task_id: int, *args, **kwargs):
        company = request.company

        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_task = TaskService.change_status(
            company_id=company.id,
            task_id=task_id,
            new_status=serializer.validated_data["status"],
        )

        detail_serializer = TaskDetailSerializer(updated_task)
        return ApiResponse.success(
            data={
                "task": detail_serializer.data,
                "message": "Task status updated successfully.",
            }
        )


# =============================================================================
# PROJECT-SCOPED TASK ENDPOINTS
# =============================================================================

class ProjectTaskListAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/projects/{project_id}/tasks/ — List tasks belonging to a specific project.
    """

    def get(self, request, project_id: int, *args, **kwargs):
        company = request.company
        params = _extract_task_query_params(request)

        queryset = TaskSelector.get_project_tasks(
            company=company,
            project_id=project_id,
            search=params.get("search"),
            status=params.get("status"),
            priority=params.get("priority"),
            assigned_to_id=params.get("assigned_to_id"),
            created_by_id=params.get("created_by_id"),
            is_overdue=params.get("is_overdue"),
            is_today=params.get("is_today"),
            is_this_week=params.get("is_this_week"),
            ordering=params.get("ordering"),
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = TaskListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.get_metadata(paginator, paginated_page)
        filters = _build_task_filter_options()

        summary = TaskSelector.get_project_task_summary(
            company=company,
            project_id=project_id,
        )

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )


class ProjectTaskSummaryAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/projects/{project_id}/tasks/summary/ — Retrieve project task aggregate metrics.
    """

    def get(self, request, project_id: int, *args, **kwargs):
        company = request.company

        summary_data = TaskSelector.get_project_task_summary(
            company=company,
            project_id=project_id,
        )

        serializer = ProjectTaskSummarySerializer(summary_data)
        return ApiResponse.success(data=serializer.data)