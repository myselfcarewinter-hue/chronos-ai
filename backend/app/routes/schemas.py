"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.database.models import (
    NotificationType,
    PriorityLevel,
    RiskLevel,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class AuthLoginResponse(BaseModel):
    authorization_url: str


class AuthCallbackResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    stats: dict[str, Any] = {}
    preferences: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TaskCreateRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=2000, description="Natural language task input")


class RiskResponse(BaseModel):
    risk_percentage: float
    risk_level: RiskLevel
    reason: str
    suggestion: str


class PriorityResponse(BaseModel):
    priority_score: float
    priority_level: PriorityLevel
    reason: str


class SubtaskResponse(BaseModel):
    id: str | None = None
    title: str
    description: str = ""
    estimated_hours: float
    status: str
    order: int


class WorkSessionResponse(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    description: str = ""


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    category: str
    difficulty: str
    estimated_hours: float
    location: str | None = None
    deadline: datetime | None = None
    status: TaskStatus
    risk: RiskResponse
    priority: PriorityResponse
    execution_plan: str = ""
    work_sessions: list[WorkSessionResponse] = []
    subtasks: list[SubtaskResponse] = []
    xp_reward: int = 100
    created_at: datetime
    updated_at: datetime


class TaskCreateResponse(BaseModel):
    task: TaskResponse
    message: str = "Task created and planned successfully"


class TaskCompleteResponse(BaseModel):
    task: TaskResponse
    xp_earned: int
    new_streak: int
    message: str


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class DashboardResponse(BaseModel):
    todays_tasks: list[TaskResponse]
    upcoming_deadlines: list[TaskResponse]
    high_risk_tasks: list[TaskResponse]
    life_score: float
    xp: int
    streak: int
    level: int
    calendar_preview: list[dict[str, Any]]
    productivity_graph: list[dict[str, Any]]
    recent_notifications: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[str] = []


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str
    details: dict[str, Any] = {}
