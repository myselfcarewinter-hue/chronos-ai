"""Task routes — create, list, complete."""

from fastapi import APIRouter, Depends, Query

from app.database.models import TaskStatus, User
from app.middleware.dependencies import (
    get_current_user,
    get_gamification_service,
    get_repos,
    get_task_pipeline,
)
from app.repositories import RepositoryContainer
from app.routes.schemas import (
    PriorityResponse,
    RiskResponse,
    SubtaskResponse,
    TaskCompleteResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskListResponse,
    TaskResponse,
    WorkSessionResponse,
)
from app.services.gamification_service import GamificationService
from app.services.task_pipeline_service import TaskPipelineService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _task_to_response(task, subtasks=None) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        category=task.category,
        difficulty=task.difficulty,
        estimated_hours=task.estimated_hours,
        location=task.location,
        deadline=task.deadline,
        status=task.status,
        risk=RiskResponse(
            risk_percentage=task.risk.risk_percentage,
            risk_level=task.risk.risk_level,
            reason=task.risk.reason,
            suggestion=task.risk.suggestion,
        ),
        priority=PriorityResponse(
            priority_score=task.priority.priority_score,
            priority_level=task.priority.priority_level,
            reason=task.priority.reason,
        ),
        execution_plan=task.execution_plan,
        work_sessions=[
            WorkSessionResponse(
                title=s.title,
                start_time=s.start_time,
                end_time=s.end_time,
                duration_hours=s.duration_hours,
                description=s.description,
            )
            for s in task.work_sessions
        ],
        subtasks=[
            SubtaskResponse(
                id=s.id,
                title=s.title,
                description=s.description,
                estimated_hours=s.estimated_hours,
                status=s.status.value,
                order=s.order,
            )
            for s in (subtasks or [])
        ],
        xp_reward=task.xp_reward,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("/create", response_model=TaskCreateResponse)
async def create_task(
    request: TaskCreateRequest,
    user: User = Depends(get_current_user),
    pipeline: TaskPipelineService = Depends(get_task_pipeline),
    repos: RepositoryContainer = Depends(get_repos),
) -> TaskCreateResponse:
    """Create a task through the full AI pipeline."""
    task = await pipeline.create_task(request.input, user)
    subtasks = await repos.subtasks.find_by_task(task.id)
    return TaskCreateResponse(
        task=_task_to_response(task, subtasks),
        message=f"Task '{task.title}' created with AI plan. Risk: {task.risk.risk_percentage:.0f}%, Priority: {task.priority.priority_level.value}.",
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: TaskStatus | None = Query(None),
    user: User = Depends(get_current_user),
    repos: RepositoryContainer = Depends(get_repos),
) -> TaskListResponse:
    """List all tasks for the authenticated user."""
    tasks = await repos.tasks.find_by_user(user.id, status=status)
    responses = []
    for task in tasks:
        subtasks = await repos.subtasks.find_by_task(task.id)
        responses.append(_task_to_response(task, subtasks))
    return TaskListResponse(tasks=responses, total=len(responses))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    repos: RepositoryContainer = Depends(get_repos),
) -> TaskResponse:
    """Get a single task by ID."""
    task = await repos.tasks.find_by_id_or_raise(task_id)
    if task.user_id != user.id:
        from app.utils.exceptions import AuthorizationError
        raise AuthorizationError("Not your task")
    subtasks = await repos.subtasks.find_by_task(task.id)
    return _task_to_response(task, subtasks)


@router.put("/{task_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    pipeline: TaskPipelineService = Depends(get_task_pipeline),
    gamification: GamificationService = Depends(get_gamification_service),
    repos: RepositoryContainer = Depends(get_repos),
) -> TaskCompleteResponse:
    """Mark a task as complete and award XP."""
    task = await pipeline.complete_task(task_id, user)
    updated_user = await gamification.award_task_completion(user, task_id, task.xp_reward)
    subtasks = await repos.subtasks.find_by_task(task.id)
    xp_earned = int(task.xp_reward * (
        gamification.settings.streak_bonus_multiplier
        if updated_user.stats.current_streak > 1 else 1.0
    ))
    return TaskCompleteResponse(
        task=_task_to_response(task, subtasks),
        xp_earned=xp_earned,
        new_streak=updated_user.stats.current_streak,
        message=f"Task completed! +{xp_earned} XP. Streak: {updated_user.stats.current_streak} days.",
    )
