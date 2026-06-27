"""Reflection Agent — nightly summaries and productivity insights."""

import logging
from datetime import datetime, timedelta, timezone

from app.agents.base_agent import BaseAgent
from app.database.models import DailySummary, ProductivityHistory, TaskStatus, User
from app.repositories.daily_summary_repository import DailySummaryRepository
from app.repositories.productivity_history_repository import ProductivityHistoryRepository
from app.repositories.task_repository import TaskRepository
from app.services.notification_service import NotificationService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC). Passes None through."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


REFLECTION_SCHEMA = """{
    "summary": "string — daily productivity summary",
    "productivity_score": "number 0-100",
    "suggestions": ["string — actionable suggestions for tomorrow"],
    "learning_insights": ["string — patterns observed about the user"],
    "weekly_summary": "string or null — only if end of week"
}"""


class ReflectionAgent(BaseAgent):
    """Generates daily/weekly summaries and productivity insights."""

    SYSTEM_INSTRUCTION = (
        "You are the Reflection Agent for Chronos AI. "
        "Generate insightful daily summaries that help users understand their productivity. "
        "Be encouraging but honest. Highlight patterns and suggest improvements."
    )

    def __init__(
        self,
        gemini_service,
        task_repo: TaskRepository,
        daily_summary_repo: DailySummaryRepository,
        productivity_repo: ProductivityHistoryRepository,
        notification_service: NotificationService,
    ) -> None:
        super().__init__(gemini_service)
        self.task_repo = task_repo
        self.daily_summary_repo = daily_summary_repo
        self.productivity_repo = productivity_repo
        self.notification_service = notification_service

    async def execute(self, user: User) -> DailySummary:
        now = utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        all_tasks = await self.task_repo.find_by_user(user.id, limit=200)
        today_completed = [
            t for t in all_tasks
            if t.status == TaskStatus.COMPLETED
            and _ensure_tz(t.completed_at)
            and today_start <= _ensure_tz(t.completed_at) <= today_end
        ]
        today_created = [
            t for t in all_tasks
            if _ensure_tz(t.created_at)
            and today_start <= _ensure_tz(t.created_at) <= today_end
        ]
        overdue = [t for t in all_tasks if t.status == TaskStatus.OVERDUE]

        hours_worked = sum(t.estimated_hours for t in today_completed)
        is_week_end = now.weekday() == 6  # Sunday

        prompt = f"""Generate a daily reflection for this user:

Date: {now.strftime('%A, %B %d, %Y')}
Tasks completed today: {len(today_completed)}
Tasks created today: {len(today_created)}
Hours worked: {hours_worked:.1f}
Overdue tasks: {len(overdue)}
Current streak: {user.stats.current_streak}
Total XP: {user.stats.total_xp}
Life score: {user.stats.life_score}
Level: {user.stats.level}

Completed tasks: {[t.title for t in today_completed]}
Overdue tasks: {[t.title for t in overdue]}

User profile:
- Preferred hours: {user.profile.preferred_work_hours}
- Delayed categories: {user.profile.frequently_delayed_categories}
- Weekly hours: {user.profile.typical_weekly_hours}

{"Generate a weekly summary as well." if is_week_end else ""}

Provide reflection as JSON."""

        try:
            result = await self._generate_json(prompt, REFLECTION_SCHEMA)
        except Exception as exc:
            logger.warning("Reflection Agent Gemini fallback: %s", exc)
            result = self._fallback_reflection(
                len(today_completed), hours_worked, user, is_week_end
            )

        productivity_score = float(result.get("productivity_score", self._calc_score(
            len(today_completed), hours_worked, user
        )))

        summary = DailySummary(
            user_id=user.id,
            date=now,
            summary=str(result.get("summary", "Day complete.")),
            tasks_completed=len(today_completed),
            tasks_created=len(today_created),
            productivity_score=productivity_score,
            suggestions=result.get("suggestions", []),
            learning_insights=result.get("learning_insights", []),
        )
        saved = await self.daily_summary_repo.create(summary)

        history = ProductivityHistory(
            user_id=user.id,
            date=now,
            tasks_completed=len(today_completed),
            hours_worked=hours_worked,
            productivity_score=productivity_score,
            xp_earned=sum(t.xp_reward for t in today_completed),
            streak_day=user.stats.current_streak,
        )
        await self.productivity_repo.create(history)

        notification_title = "Weekly Summary" if is_week_end else "Daily Summary"
        summary_text = result.get("weekly_summary") if is_week_end else result.get("summary")
        await self.notification_service.send_summary(
            user_id=user.id,
            title=notification_title,
            summary=str(summary_text or saved.summary),
        )

        logger.info("Reflection complete for user %s: score=%.0f", user.id, productivity_score)
        return saved

    async def execute_all_users(self) -> list[DailySummary]:
        """Run reflection for all users — called by scheduler."""
        from app.repositories.user_repository import UserRepository
        from app.database.db import Database

        user_repo = UserRepository(Database.get_db())
        users = await user_repo.find_many(limit=1000)
        summaries: list[DailySummary] = []

        for user in users:
            try:
                summary = await self.execute(user)
                summaries.append(summary)
            except Exception as exc:
                logger.error("Reflection failed for user %s: %s", user.id, exc)

        return summaries

    def _calc_score(self, completed: int, hours: float, user: User) -> float:
        base = min(completed * 20, 60) + min(hours * 5, 30)
        streak_bonus = min(user.stats.current_streak * 2, 10)
        return min(100, base + streak_bonus)

    def _fallback_reflection(
        self,
        completed: int,
        hours: float,
        user: User,
        is_week_end: bool,
    ) -> dict:
        if completed == 0:
            summary = "No tasks completed today. Tomorrow is a fresh start!"
            suggestions = ["Pick your highest priority task and start with 25 minutes"]
        elif completed >= 3:
            summary = f"Productive day! Completed {completed} tasks ({hours:.1f}h of work)."
            suggestions = ["Maintain momentum — tackle tomorrow's highest priority first"]
        else:
            summary = f"Completed {completed} task(s) today. Steady progress!"
            suggestions = ["Try time-blocking tomorrow for better focus"]

        result = {
            "summary": summary,
            "productivity_score": self._calc_score(completed, hours, user),
            "suggestions": suggestions,
            "learning_insights": [],
        }

        if is_week_end:
            result["weekly_summary"] = (
                f"Week in review: {user.stats.total_tasks_completed} total tasks, "
                f"streak at {user.stats.current_streak} days, life score {user.stats.life_score:.0f}."
            )

        return result
