"""APScheduler background job configuration."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import Settings, get_settings
from app.database.db import Database

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_guardian() -> None:
    """Hourly guardian scan for all users."""
    from app.agents.guardian_agent import GuardianAgent
    from app.agents.rescue_agent import RescueAgent
    from app.agents.planner_agent import PlannerAgent
    from app.repositories import get_repositories
    from app.services.gemini_service import get_gemini_service
    from app.services.notification_service import NotificationService
    from app.services.calendar_service import CalendarService
    from app.services.oauth_service import OAuthService

    try:
        repos = get_repositories(Database.get_db())
        gemini = get_gemini_service()
        oauth = OAuthService(repos.users, get_settings())
        calendar = CalendarService(repos.calendar_events, oauth, get_settings())
        notifications = NotificationService(repos.notifications)
        planner = PlannerAgent(gemini, repos.subtasks, calendar)
        rescue = RescueAgent(gemini, repos.tasks, planner, notifications)
        guardian = GuardianAgent(gemini, repos.tasks, repos.users, notifications, rescue)

        result = await guardian.execute()
        logger.info("Guardian job complete: %s", result)
    except Exception as exc:
        logger.error("Guardian job failed: %s", exc)


async def _run_reflection() -> None:
    """Nightly reflection for all users."""
    from app.agents.reflection_agent import ReflectionAgent
    from app.repositories import get_repositories
    from app.services.gemini_service import get_gemini_service
    from app.services.notification_service import NotificationService

    try:
        repos = get_repositories(Database.get_db())
        gemini = get_gemini_service()
        notifications = NotificationService(repos.notifications)
        reflection = ReflectionAgent(
            gemini, repos.tasks, repos.daily_summaries, repos.productivity_history, notifications
        )

        summaries = await reflection.execute_all_users()
        logger.info("Reflection job complete: %d summaries generated", len(summaries))
    except Exception as exc:
        logger.error("Reflection job failed: %s", exc)


def setup_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Configure and return the APScheduler instance."""
    settings = settings or get_settings()

    scheduler.add_job(
        _run_guardian,
        trigger=IntervalTrigger(minutes=settings.guardian_interval_minutes),
        id="guardian_agent",
        name="Guardian Agent — Hourly Monitoring",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_reflection,
        trigger=CronTrigger(
            hour=settings.reflection_hour,
            minute=settings.reflection_minute,
        ),
        id="reflection_agent",
        name="Reflection Agent — Nightly Summary",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: Guardian every %d min, Reflection at %02d:%02d",
        settings.guardian_interval_minutes,
        settings.reflection_hour,
        settings.reflection_minute,
    )
    return scheduler
