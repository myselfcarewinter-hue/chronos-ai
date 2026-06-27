"""Planner Agent — breaks tasks into subtasks and schedules work sessions."""

import logging
from datetime import datetime, timedelta
from typing import Any

from app.agents.base_agent import BaseAgent
from app.database.models import Subtask, SubtaskStatus, Task, User, WorkSession
from app.repositories.subtask_repository import SubtaskRepository
from app.services.calendar_service import CalendarService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

PLANNER_SCHEMA = """{
    "execution_plan": "string — overall strategy narrative",
    "subtasks": [
        {
            "title": "string",
            "description": "string",
            "estimated_hours": "number",
            "order": "integer starting from 0"
        }
    ],
    "sessions": [
        {
            "title": "string",
            "duration_hours": "number",
            "description": "string"
        }
    ]
}"""


class PlannerAgent(BaseAgent):
    """Creates execution plans, subtasks, and calendar events."""

    SYSTEM_INSTRUCTION = (
        "You are the Planner Agent for Chronos AI. "
        "Break tasks into actionable subtasks and schedule focused work sessions. "
        "Consider the user's preferred work hours and available time. "
        "Each session should be 1-3 hours for optimal focus."
    )

    def __init__(
        self,
        gemini_service,
        subtask_repo: SubtaskRepository,
        calendar_service: CalendarService,
    ) -> None:
        super().__init__(gemini_service)
        self.subtask_repo = subtask_repo
        self.calendar_service = calendar_service

    async def execute(
        self,
        task_data: dict[str, Any],
        user: User,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        preferred_hours = user.profile.preferred_work_hours
        now = utc_now()
        deadline = task_data.get("deadline", now + timedelta(days=7))

        prompt = f"""Create an execution plan for this task:

Title: {task_data.get('title')}
Description: {task_data.get('description', '')}
Category: {task_data.get('category')}
Difficulty: {task_data.get('difficulty')}
Estimated total hours: {task_data.get('estimated_hours')}
Deadline: {deadline.isoformat() if isinstance(deadline, datetime) else deadline}
Priority: {task_data.get('priority_level', 'medium')}
Risk: {task_data.get('risk_percentage', 0):.0f}%

User preferences:
- Preferred work hours: {preferred_hours}
- Average completion by category: {user.profile.average_completion_time_by_category}

Break into 3-8 subtasks and schedule work sessions totaling the estimated hours.
Sessions should be 1-3 hours each, spread before the deadline."""

        try:
            result = await self._generate_json(prompt, PLANNER_SCHEMA)
        except Exception as exc:
            logger.warning("Planner Agent Gemini fallback: %s", exc)
            result = self._fallback_plan(task_data)

        subtasks = await self._create_subtasks(result.get("subtasks", []), task_id)
        sessions = await self._schedule_sessions(
            result.get("sessions", []),
            user,
            task_data,
            task_id,
            now,
            deadline if isinstance(deadline, datetime) else now + timedelta(days=7),
        )

        return {
            "execution_plan": result.get("execution_plan", "Work through subtasks in order."),
            "subtasks": subtasks,
            "work_sessions": sessions,
        }

    async def _create_subtasks(
        self,
        subtask_data: list[dict],
        task_id: str | None,
    ) -> list[Subtask]:
        if not task_id:
            return []

        created: list[Subtask] = []
        for item in subtask_data:
            subtask = Subtask(
                task_id=task_id,
                title=str(item.get("title", "Subtask")),
                description=str(item.get("description", "")),
                estimated_hours=float(item.get("estimated_hours", 1.0)),
                order=int(item.get("order", len(created))),
                status=SubtaskStatus.PENDING,
            )
            saved = await self.subtask_repo.create(subtask)
            created.append(saved)
        return created

    async def _schedule_sessions(
        self,
        session_data: list[dict],
        user: User,
        task_data: dict[str, Any],
        task_id: str | None,
        start: datetime,
        deadline: datetime,
    ) -> list[WorkSession]:
        sessions: list[WorkSession] = []
        available_slots = await self.calendar_service.find_available_slots(
            user=user,
            duration_hours=2.0,
            start=start,
            end=deadline,
            preferred_hours=user.profile.preferred_work_hours,
        )

        slot_index = 0
        for item in session_data:
            duration = float(item.get("duration_hours", 2.0))
            title = str(item.get("title", f"Work on: {task_data.get('title', 'Task')}"))

            if slot_index < len(available_slots):
                session_start, session_end = available_slots[slot_index]
                slot_index += 1
            else:
                session_start = start + timedelta(hours=slot_index * 3)
                session_end = session_start + timedelta(hours=duration)
                slot_index += 1

            session = WorkSession(
                title=title,
                start_time=session_start,
                end_time=session_end,
                duration_hours=duration,
                description=str(item.get("description", "")),
            )
            sessions.append(session)

            if task_id:
                try:
                    await self.calendar_service.create_event(
                        user=user,
                        title=title,
                        start_time=session_start,
                        end_time=session_end,
                        description=session.description,
                        location=task_data.get("location"),
                        task_id=task_id,
                    )
                except Exception as exc:
                    logger.warning("Calendar event creation skipped: %s", exc)

        return sessions

    def _fallback_plan(self, task_data: dict[str, Any]) -> dict[str, Any]:
        hours = float(task_data.get("estimated_hours", 2.0))
        title = task_data.get("title", "Task")
        num_subtasks = max(2, min(5, int(hours / 2)))

        subtasks = []
        per_subtask = hours / num_subtasks
        for i in range(num_subtasks):
            subtasks.append({
                "title": f"{title} — Part {i + 1}/{num_subtasks}",
                "description": f"Complete part {i + 1} of {title}",
                "estimated_hours": round(per_subtask, 1),
                "order": i,
            })

        sessions = []
        remaining = hours
        session_num = 1
        while remaining > 0:
            duration = min(remaining, 2.0)
            sessions.append({
                "title": f"Focus Session {session_num}: {title}",
                "duration_hours": duration,
                "description": f"Focused work session for {title}",
            })
            remaining -= duration
            session_num += 1

        return {
            "execution_plan": f"Break '{title}' into {num_subtasks} parts and complete in focused sessions.",
            "subtasks": subtasks,
            "sessions": sessions,
        }
