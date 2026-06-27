"""Pydantic models for MongoDB documents."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.utils.helpers import utc_now


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class SubtaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class NotificationType(str, Enum):
    REMINDER = "reminder"
    RISK_ALERT = "risk_alert"
    RESCUE = "rescue"
    REWARD = "reward"
    SUMMARY = "summary"
    MOTIVATION = "motivation"


class RewardType(str, Enum):
    XP = "xp"
    STREAK = "streak"
    BADGE = "badge"
    LEVEL_UP = "level_up"


# ---------------------------------------------------------------------------
# Embedded / value objects
# ---------------------------------------------------------------------------


class UserPreferences(BaseModel):
    preferred_work_hours_start: int = 9
    preferred_work_hours_end: int = 17
    timezone: str = "UTC"
    notification_enabled: bool = True


class UserStats(BaseModel):
    total_tasks_completed: int = 0
    total_xp: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    life_score: float = 50.0
    level: int = 1
    average_completion_hours: float = 0.0


class UserProfile(BaseModel):
    preferred_work_hours: list[int] = Field(default_factory=lambda: [9, 10, 14, 15, 16])
    average_completion_time_by_category: dict[str, float] = Field(default_factory=dict)
    frequently_delayed_categories: list[str] = Field(default_factory=list)
    typical_weekly_hours: float = 20.0
    productivity_score_history: list[float] = Field(default_factory=list)


class RiskAnalysis(BaseModel):
    risk_percentage: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    reason: str = ""
    suggestion: str = ""


class PriorityAnalysis(BaseModel):
    priority_score: float = 0.0
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    reason: str = ""


class WorkSession(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    description: str = ""


# ---------------------------------------------------------------------------
# Document models
# ---------------------------------------------------------------------------


class User(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    google_id: str
    email: str
    name: str
    avatar_url: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expiry: datetime | None = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    stats: UserStats = Field(default_factory=UserStats)
    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class Subtask(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    task_id: str
    title: str
    description: str = ""
    estimated_hours: float = 1.0
    status: SubtaskStatus = SubtaskStatus.PENDING
    order: int = 0
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class Task(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    title: str
    description: str = ""
    raw_input: str = ""
    category: str = "general"
    difficulty: str = "medium"
    estimated_hours: float = 1.0
    location: str | None = None
    deadline: datetime | None = None
    status: TaskStatus = TaskStatus.PENDING
    risk: RiskAnalysis = Field(default_factory=RiskAnalysis)
    priority: PriorityAnalysis = Field(default_factory=PriorityAnalysis)
    execution_plan: str = ""
    work_sessions: list[WorkSession] = Field(default_factory=list)
    xp_reward: int = 100
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class CalendarEvent(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    task_id: str
    subtask_id: str | None = None
    google_event_id: str | None = None
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    location: str | None = None
    synced: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class Reward(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    task_id: str | None = None
    reward_type: RewardType
    amount: int = 0
    badge_name: str | None = None
    message: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class Notification(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    notification_type: NotificationType
    title: str
    message: str
    read: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class DailySummary(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    date: datetime
    summary: str = ""
    tasks_completed: int = 0
    tasks_created: int = 0
    productivity_score: float = 0.0
    suggestions: list[str] = Field(default_factory=list)
    learning_insights: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}


class ProductivityHistory(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    date: datetime
    tasks_completed: int = 0
    hours_worked: float = 0.0
    productivity_score: float = 0.0
    xp_earned: int = 0
    streak_day: int = 0
    created_at: datetime = Field(default_factory=utc_now)

    model_config = {"populate_by_name": True}
