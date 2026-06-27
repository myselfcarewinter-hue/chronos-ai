"""FastAPI dependency injection container."""

from functools import lru_cache

from fastapi import Depends, Header

from app.agents.guardian_agent import GuardianAgent
from app.agents.intake_agent import IntakeAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.priority_agent import PriorityAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.rescue_agent import RescueAgent
from app.agents.risk_agent import RiskPredictionAgent
from app.config.settings import Settings, get_settings
from app.database.db import get_database
from app.database.models import User
from app.repositories import RepositoryContainer, get_repositories
from app.services.calendar_service import CalendarService
from app.services.gamification_service import GamificationService
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.notification_service import NotificationService
from app.services.oauth_service import OAuthService
from app.services.task_pipeline_service import TaskPipelineService
from app.utils.exceptions import AuthorizationError


# ---------------------------------------------------------------------------
# Core dependencies
# ---------------------------------------------------------------------------


def get_settings_dep() -> Settings:
    return get_settings()


def get_repos() -> RepositoryContainer:
    return get_repositories(get_database())


def get_gemini(settings: Settings = Depends(get_settings_dep)) -> GeminiService:
    return get_gemini_service(settings)


# ---------------------------------------------------------------------------
# Service dependencies
# ---------------------------------------------------------------------------


def get_oauth_service(
    repos: RepositoryContainer = Depends(get_repos),
    settings: Settings = Depends(get_settings_dep),
) -> OAuthService:
    return OAuthService(repos.users, settings)


def get_notification_service(
    repos: RepositoryContainer = Depends(get_repos),
) -> NotificationService:
    return NotificationService(repos.notifications)


def get_calendar_service(
    repos: RepositoryContainer = Depends(get_repos),
    oauth: OAuthService = Depends(get_oauth_service),
    settings: Settings = Depends(get_settings_dep),
) -> CalendarService:
    return CalendarService(repos.calendar_events, oauth, settings)


def get_gamification_service(
    repos: RepositoryContainer = Depends(get_repos),
    notifications: NotificationService = Depends(get_notification_service),
    settings: Settings = Depends(get_settings_dep),
) -> GamificationService:
    return GamificationService(repos.users, repos.rewards, notifications, settings)


# ---------------------------------------------------------------------------
# Agent dependencies
# ---------------------------------------------------------------------------


def get_intake_agent(gemini: GeminiService = Depends(get_gemini)) -> IntakeAgent:
    return IntakeAgent(gemini)


def get_risk_agent(gemini: GeminiService = Depends(get_gemini)) -> RiskPredictionAgent:
    return RiskPredictionAgent(gemini)


def get_priority_agent(gemini: GeminiService = Depends(get_gemini)) -> PriorityAgent:
    return PriorityAgent(gemini)


def get_planner_agent(
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
    calendar: CalendarService = Depends(get_calendar_service),
) -> PlannerAgent:
    return PlannerAgent(gemini, repos.subtasks, calendar)


def get_memory_agent(
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
) -> MemoryAgent:
    return MemoryAgent(gemini, repos.users, repos.tasks)


def get_rescue_agent(
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
    planner: PlannerAgent = Depends(get_planner_agent),
    notifications: NotificationService = Depends(get_notification_service),
) -> RescueAgent:
    return RescueAgent(gemini, repos.tasks, planner, notifications)


def get_guardian_agent(
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
    notifications: NotificationService = Depends(get_notification_service),
    rescue: RescueAgent = Depends(get_rescue_agent),
) -> GuardianAgent:
    return GuardianAgent(gemini, repos.tasks, repos.users, notifications, rescue)


def get_reflection_agent(
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
    notifications: NotificationService = Depends(get_notification_service),
) -> ReflectionAgent:
    return ReflectionAgent(
        gemini, repos.tasks, repos.daily_summaries, repos.productivity_history, notifications
    )


def get_task_pipeline(
    intake: IntakeAgent = Depends(get_intake_agent),
    risk: RiskPredictionAgent = Depends(get_risk_agent),
    priority: PriorityAgent = Depends(get_priority_agent),
    planner: PlannerAgent = Depends(get_planner_agent),
    memory: MemoryAgent = Depends(get_memory_agent),
    repos: RepositoryContainer = Depends(get_repos),
    calendar: CalendarService = Depends(get_calendar_service),
) -> TaskPipelineService:
    return TaskPipelineService(
        intake, risk, priority, planner, memory,
        repos.tasks, repos.subtasks, calendar,
    )


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    oauth: OAuthService = Depends(get_oauth_service),
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise AuthorizationError("Invalid authorization header")
    token = authorization[7:]
    return await oauth.get_current_user(token)
