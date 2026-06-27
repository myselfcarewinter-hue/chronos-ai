"""Dashboard route — aggregated user productivity view."""

from datetime import timedelta

from fastapi import APIRouter, Depends

from app.database.models import User
from app.middleware.dependencies import get_current_user, get_repos
from app.repositories import RepositoryContainer
from app.routes.schemas import DashboardResponse, TaskResponse
from app.routes.tasks import _task_to_response
from app.utils.helpers import utc_now

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user: User = Depends(get_current_user),
    repos: RepositoryContainer = Depends(get_repos),
) -> DashboardResponse:
    """Return comprehensive dashboard data."""
    now = utc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    todays_tasks_raw = await repos.tasks.find_due_today(user.id, today_start, today_end)
    upcoming = await repos.tasks.find_upcoming_deadlines(user.id, now + timedelta(days=7))
    high_risk = await repos.tasks.find_high_risk(user.id, threshold=50.0)
    calendar_events = await repos.calendar_events.find_by_user(user.id, limit=10)
    productivity = await repos.productivity_history.find_last_n_days(user.id, days=30)
    notifications = await repos.notifications.find_unread_by_user(user.id, limit=5)

    todays_tasks = []
    for task in todays_tasks_raw:
        subtasks = await repos.subtasks.find_by_task(task.id)
        todays_tasks.append(_task_to_response(task, subtasks))

    upcoming_responses = []
    for task in upcoming[:5]:
        subtasks = await repos.subtasks.find_by_task(task.id)
        upcoming_responses.append(_task_to_response(task, subtasks))

    high_risk_responses = []
    for task in high_risk[:5]:
        subtasks = await repos.subtasks.find_by_task(task.id)
        high_risk_responses.append(_task_to_response(task, subtasks))

    return DashboardResponse(
        todays_tasks=todays_tasks,
        upcoming_deadlines=upcoming_responses,
        high_risk_tasks=high_risk_responses,
        life_score=user.stats.life_score,
        xp=user.stats.total_xp,
        streak=user.stats.current_streak,
        level=user.stats.level,
        calendar_preview=[
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "synced": e.synced,
            }
            for e in calendar_events
        ],
        productivity_graph=[
            {
                "date": p.date.isoformat(),
                "score": p.productivity_score,
                "tasks_completed": p.tasks_completed,
                "hours_worked": p.hours_worked,
                "xp_earned": p.xp_earned,
            }
            for p in productivity
        ],
        recent_notifications=[
            {
                "id": n.id,
                "type": n.notification_type.value,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
    )
