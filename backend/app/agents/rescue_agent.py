"""Rescue Agent — rebuilds schedules when deadline risk is high."""

import logging
from datetime import timedelta

from app.agents.base_agent import BaseAgent
from app.agents.planner_agent import PlannerAgent
from app.database.models import Task, User
from app.repositories.task_repository import TaskRepository
from app.services.notification_service import NotificationService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

RESCUE_SCHEMA = """{
    "strategy": "string — recovery strategy description",
    "motivation_message": "string — encouraging message for the user",
    "rescheduled": "boolean — whether schedule was rebuilt",
    "actions_taken": ["string — list of specific actions"]
}"""


class RescueAgent(BaseAgent):
    """Automatically rebuilds schedule and suggests recovery when risk is high."""

    SYSTEM_INSTRUCTION = (
        "You are the Rescue Agent for Chronos AI. "
        "When a user falls behind, create actionable recovery strategies. "
        "Be empathetic but practical. Focus on what CAN be done, not what was missed."
    )

    def __init__(
        self,
        gemini_service,
        task_repo: TaskRepository,
        planner_agent: PlannerAgent,
        notification_service: NotificationService,
    ) -> None:
        super().__init__(gemini_service)
        self.task_repo = task_repo
        self.planner_agent = planner_agent
        self.notification_service = notification_service

    async def execute(self, user: User, task: Task) -> dict:
        now = utc_now()
        hours_left = 0.0
        if task.deadline:
            hours_left = max(0, (task.deadline - now).total_seconds() / 3600)

        prompt = f"""Create a rescue plan for this at-risk task:

Task: {task.title}
Category: {task.category}
Difficulty: {task.difficulty}
Estimated hours remaining: {task.estimated_hours}
Deadline: {task.deadline.isoformat() if task.deadline else 'None'}
Hours until deadline: {hours_left:.1f}
Risk: {task.risk.risk_percentage:.0f}% — {task.risk.reason}
Current plan: {task.execution_plan}

User stats:
- Streak: {user.stats.current_streak}
- Tasks completed: {user.stats.total_tasks_completed}
- Life score: {user.stats.life_score}

Suggest a realistic recovery strategy and motivational message."""

        try:
            result = await self._generate_json(prompt, RESCUE_SCHEMA)
        except Exception as exc:
            logger.warning("Rescue Agent Gemini fallback: %s", exc)
            result = self._fallback_rescue(task, hours_left)

        rescheduled = False
        if hours_left > 0 and task.risk.risk_percentage >= 70:
            try:
                plan_result = await self.planner_agent.execute(
                    task_data={
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "difficulty": task.difficulty,
                        "estimated_hours": task.estimated_hours,
                        "deadline": task.deadline,
                        "location": task.location,
                    },
                    user=user,
                    task_id=task.id,
                )
                await self.task_repo.update(task.id, {
                    "execution_plan": plan_result["execution_plan"],
                    "work_sessions": [s.model_dump() for s in plan_result["work_sessions"]],
                })
                rescheduled = True
                result["rescheduled"] = True
            except Exception as exc:
                logger.error("Rescue rescheduling failed: %s", exc)

        await self.notification_service.send_rescue(
            user_id=user.id,
            task_title=task.title,
            strategy=result.get("strategy", "Focus on completing the highest-priority parts first."),
            motivation=result.get("motivation_message", "You've got this! One step at a time."),
        )

        return {
            "task_id": task.id,
            "strategy": result.get("strategy"),
            "motivation": result.get("motivation_message"),
            "rescheduled": rescheduled,
            "actions": result.get("actions_taken", []),
        }

    def _fallback_rescue(self, task: Task, hours_left: float) -> dict:
        actions = []
        if hours_left < task.estimated_hours:
            actions.append("Focus on the minimum viable deliverable")
            actions.append("Break remaining work into 1-hour sprints")
            strategy = (
                f"Time is tight ({hours_left:.0f}h left, {task.estimated_hours:.0f}h needed). "
                "Prioritize core requirements and defer optional parts."
            )
        else:
            actions.append("Reschedule remaining work into focused sessions")
            actions.append("Block calendar time immediately")
            strategy = "Rebuild your schedule with focused work blocks before the deadline."

        return {
            "strategy": strategy,
            "motivation_message": (
                f"Don't panic — '{task.title}' is still achievable. "
                "Start with the most important part right now."
            ),
            "rescheduled": False,
            "actions_taken": actions,
        }
