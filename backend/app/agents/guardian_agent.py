"""Guardian Agent — hourly monitoring of tasks and deadlines."""

import logging
from datetime import datetime, timedelta

from app.agents.base_agent import BaseAgent
from app.agents.rescue_agent import RescueAgent
from app.database.models import NotificationType, TaskStatus, User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class GuardianAgent(BaseAgent):
    """Runs hourly to monitor progress and trigger rescues."""

    SYSTEM_INSTRUCTION = (
        "You are the Guardian Agent for Chronos AI. "
        "Monitor user tasks and identify problems before they become crises."
    )

    def __init__(
        self,
        gemini_service,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        notification_service: NotificationService,
        rescue_agent: RescueAgent,
    ) -> None:
        super().__init__(gemini_service)
        self.task_repo = task_repo
        self.user_repo = user_repo
        self.notification_service = notification_service
        self.rescue_agent = rescue_agent

    async def execute(self, user_id: str | None = None) -> dict:
        """Monitor all users or a specific user."""
        if user_id:
            user = await self.user_repo.find_by_id(user_id)
            if not user:
                return {"monitored": 0, "actions": []}
            return await self._monitor_user(user)

        users = await self.user_repo.find_many(limit=1000)
        total_actions: list[dict] = []
        for user in users:
            result = await self._monitor_user(user)
            total_actions.extend(result.get("actions", []))

        logger.info("Guardian scan complete: %d actions taken", len(total_actions))
        return {"monitored": len(users), "actions": total_actions}

    async def _monitor_user(self, user: User) -> dict:
        now = utc_now()
        actions: list[dict] = []

        overdue = await self.task_repo.find_overdue(user.id, now)
        for task in overdue:
            await self.task_repo.update(task.id, {"status": TaskStatus.OVERDUE.value})
            await self.notification_service.send(
                user_id=user.id,
                notification_type=NotificationType.RISK_ALERT,
                title=f"Overdue: {task.title}",
                message=f"Task '{task.title}' is past its deadline. Rescue plan being generated.",
            )
            actions.append({"type": "overdue", "task_id": task.id})

        high_risk = await self.task_repo.find_high_risk(user.id, threshold=70.0)
        for task in high_risk:
            rescue_result = await self.rescue_agent.execute(user, task)
            actions.append({"type": "rescue", "task_id": task.id, "result": rescue_result})

        upcoming = await self.task_repo.find_upcoming_deadlines(
            user.id, now + timedelta(hours=24)
        )
        for task in upcoming:
            if task.risk.risk_percentage >= 50:
                await self.notification_service.send_risk_alert(
                    user_id=user.id,
                    task_title=task.title,
                    risk_percentage=task.risk.risk_percentage,
                    suggestion=task.risk.suggestion,
                )
                actions.append({"type": "risk_alert", "task_id": task.id})

        return {"user_id": user.id, "actions": actions}
