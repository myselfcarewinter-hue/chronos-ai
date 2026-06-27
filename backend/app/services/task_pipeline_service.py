"""Task pipeline orchestrator — chains all agents for task creation."""

import logging
from datetime import timedelta

from app.agents.intake_agent import IntakeAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.priority_agent import PriorityAgent
from app.agents.risk_agent import RiskPredictionAgent
from app.database.models import Task, TaskStatus, User
from app.repositories.subtask_repository import SubtaskRepository
from app.repositories.task_repository import TaskRepository
from app.services.calendar_service import CalendarService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class TaskPipelineService:
    """Orchestrates the full agent pipeline: Intake → Risk → Priority → Planner → Store."""

    def __init__(
        self,
        intake_agent: IntakeAgent,
        risk_agent: RiskPredictionAgent,
        priority_agent: PriorityAgent,
        planner_agent: PlannerAgent,
        memory_agent: MemoryAgent,
        task_repo: TaskRepository,
        subtask_repo: SubtaskRepository,
        calendar_service: CalendarService,
    ) -> None:
        self.intake = intake_agent
        self.risk = risk_agent
        self.priority = priority_agent
        self.planner = planner_agent
        self.memory = memory_agent
        self.task_repo = task_repo
        self.subtask_repo = subtask_repo
        self.calendar_service = calendar_service

    async def create_task(self, raw_input: str, user: User) -> Task:
        logger.info("Pipeline started for user %s: %s", user.id, raw_input[:80])

        # Step 1: Intake — parse natural language
        intake_data = await self.intake.execute(
            raw_input,
            user_timezone=user.preferences.timezone,
        )
        logger.info("Intake complete: %s", intake_data["title"])

        # Step 2: Calculate calendar availability
        now = utc_now()
        deadline = intake_data["deadline"]
        available_slots = await self.calendar_service.find_available_slots(
            user=user,
            duration_hours=intake_data["estimated_hours"],
            start=now,
            end=deadline,
            preferred_hours=user.profile.preferred_work_hours,
        )
        available_hours = sum(
            (end - start).total_seconds() / 3600 for start, end in available_slots
        )
        busy_hours = max(0, (deadline - now).total_seconds() / 3600 - available_hours)

        # Step 3: Risk — predict failure probability
        risk = await self.risk.execute(
            task_data=intake_data,
            user=user,
            available_hours=available_hours,
            busy_hours=busy_hours,
        )
        logger.info("Risk assessment: %.0f%% (%s)", risk.risk_percentage, risk.risk_level.value)

        # Step 4: Priority — calculate priority score
        priority = await self.priority.execute(
            task_data=intake_data,
            risk=risk,
            user=user,
        )
        logger.info("Priority: %.0f (%s)", priority.priority_score, priority.priority_level.value)

        # Step 5: Store task in database
        task = Task(
            user_id=user.id,
            title=intake_data["title"],
            description=intake_data.get("description", ""),
            raw_input=raw_input,
            category=intake_data["category"],
            difficulty=intake_data["difficulty"],
            estimated_hours=intake_data["estimated_hours"],
            location=intake_data.get("location"),
            deadline=deadline,
            status=TaskStatus.PENDING,
            risk=risk,
            priority=priority,
            xp_reward=100,
        )
        saved_task = await self.task_repo.create(task)

        # Step 6: Planner — create subtasks, sessions, calendar events
        plan_data = {
            **intake_data,
            "priority_level": priority.priority_level.value,
            "risk_percentage": risk.risk_percentage,
        }
        plan_result = await self.planner.execute(
            task_data=plan_data,
            user=user,
            task_id=saved_task.id,
        )

        # Step 7: Update task with plan
        updated = await self.task_repo.update(saved_task.id, {
            "execution_plan": plan_result["execution_plan"],
            "work_sessions": [s.model_dump() for s in plan_result["work_sessions"]],
            "status": TaskStatus.IN_PROGRESS.value,
        })

        # Step 8: Memory — update user profile
        await self.memory.execute(user)

        final_task = updated or saved_task
        logger.info("Pipeline complete: task %s created with %d subtasks",
                     final_task.id, len(plan_result.get("subtasks", [])))
        return final_task

    async def complete_task(self, task_id: str, user: User) -> Task:
        task = await self.task_repo.find_by_id_or_raise(task_id)
        if task.user_id != user.id:
            from app.utils.exceptions import AuthorizationError
            raise AuthorizationError("Not your task")

        updated = await self.task_repo.update(task_id, {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": utc_now(),
        })
        await self.memory.execute(user, completed_task=updated or task)
        return updated or task
