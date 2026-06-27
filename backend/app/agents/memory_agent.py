"""Memory Agent — maintains long-term user productivity profile."""

import logging
from datetime import datetime, timedelta, timezone

from app.agents.base_agent import BaseAgent
from app.database.models import Task, TaskStatus, User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Return a timezone-aware datetime (UTC). No-ops if already aware; None passes through."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class MemoryAgent(BaseAgent):
    """Learns user patterns and updates long-term profile."""

    SYSTEM_INSTRUCTION = (
        "You are the Memory Agent for Chronos AI. "
        "Analyze user productivity patterns and update their profile for better future planning."
    )

    def __init__(
        self,
        gemini_service,
        user_repo: UserRepository,
        task_repo: TaskRepository,
    ) -> None:
        super().__init__(gemini_service)
        self.user_repo = user_repo
        self.task_repo = task_repo

    async def execute(self, user: User, completed_task: Task | None = None) -> User:
        """Update user profile based on task history and optional just-completed task."""
        all_tasks = await self.task_repo.find_by_user(user.id, limit=200)
        profile = user.profile.model_dump()

        profile["preferred_work_hours"] = self._learn_preferred_hours(all_tasks)
        profile["average_completion_time_by_category"] = self._learn_completion_times(all_tasks)
        profile["frequently_delayed_categories"] = self._learn_delayed_categories(all_tasks)
        profile["typical_weekly_hours"] = self._learn_weekly_hours(all_tasks)

        if completed_task:
            await self._update_from_completion(profile, completed_task)

        updated = await self.user_repo.update(user.id, {"profile": profile})
        logger.info("Memory Agent updated profile for user %s", user.id)
        return updated or user

    def _learn_preferred_hours(self, tasks: list[Task]) -> list[int]:
        hour_counts: dict[int, int] = {}
        for task in tasks:
            completed_at = _ensure_tz(task.completed_at)
            if completed_at:
                hour = completed_at.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if not hour_counts:
            return [9, 10, 14, 15, 16]

        sorted_hours = sorted(hour_counts, key=hour_counts.get, reverse=True)
        return sorted_hours[:5]

    def _learn_completion_times(self, tasks: list[Task]) -> dict[str, float]:
        category_times: dict[str, list[float]] = {}
        for task in tasks:
            completed_at = _ensure_tz(task.completed_at)
            created_at = _ensure_tz(task.created_at)
            if task.status == TaskStatus.COMPLETED and completed_at and created_at:
                actual_hours = (completed_at - created_at).total_seconds() / 3600
                category_times.setdefault(task.category, []).append(actual_hours)

        return {
            cat: round(sum(times) / len(times), 1)
            for cat, times in category_times.items()
            if times
        }

    def _learn_delayed_categories(self, tasks: list[Task]) -> list[str]:
        delayed: dict[str, int] = {}
        for task in tasks:
            if task.status in (TaskStatus.OVERDUE, TaskStatus.COMPLETED):
                deadline = _ensure_tz(task.deadline)
                completed_at = _ensure_tz(task.completed_at)
                if deadline and completed_at and completed_at > deadline:
                    delayed[task.category] = delayed.get(task.category, 0) + 1
                elif task.status == TaskStatus.OVERDUE:
                    delayed[task.category] = delayed.get(task.category, 0) + 1

        threshold = 2
        return [cat for cat, count in delayed.items() if count >= threshold]

    def _learn_weekly_hours(self, tasks: list[Task]) -> float:
        now = utc_now()
        week_ago = now - timedelta(days=7)
        total_hours = 0.0

        for task in tasks:
            completed_at = _ensure_tz(task.completed_at)
            if task.status == TaskStatus.COMPLETED and completed_at:
                if completed_at >= week_ago:
                    total_hours += task.estimated_hours

        return round(total_hours, 1)

    async def _update_from_completion(self, profile: dict, task: Task) -> None:
        completed_at = _ensure_tz(task.completed_at)
        created_at = _ensure_tz(task.created_at)
        if completed_at and created_at:
            actual = (completed_at - created_at).total_seconds() / 3600
            cat = task.category
            existing = profile["average_completion_time_by_category"].get(cat, actual)
            profile["average_completion_time_by_category"][cat] = round(
                (existing + actual) / 2, 1
            )

        scores = profile.get("productivity_score_history", [])
        score = min(100, 50 + task.estimated_hours * 5)
        scores.append(score)
        profile["productivity_score_history"] = scores[-30:]
