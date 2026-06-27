"""Notification service for user alerts and motivation."""

import logging

from app.database.models import Notification, NotificationType
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Creates and manages user notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self.notification_repo = notification_repo

    async def send(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        metadata: dict | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            metadata=metadata or {},
        )
        created = await self.notification_repo.create(notification)
        logger.info("Notification sent to user %s: %s", user_id, title)
        return created

    async def send_risk_alert(
        self,
        user_id: str,
        task_title: str,
        risk_percentage: float,
        suggestion: str,
    ) -> Notification:
        return await self.send(
            user_id=user_id,
            notification_type=NotificationType.RISK_ALERT,
            title=f"High Risk: {task_title}",
            message=f"This task has a {risk_percentage:.0f}% failure risk. {suggestion}",
            metadata={"risk_percentage": risk_percentage},
        )

    async def send_rescue(
        self,
        user_id: str,
        task_title: str,
        strategy: str,
        motivation: str,
    ) -> Notification:
        return await self.send(
            user_id=user_id,
            notification_type=NotificationType.RESCUE,
            title=f"Rescue Plan: {task_title}",
            message=f"{strategy}\n\n{motivation}",
        )

    async def send_reward(
        self,
        user_id: str,
        message: str,
        xp_amount: int,
    ) -> Notification:
        return await self.send(
            user_id=user_id,
            notification_type=NotificationType.REWARD,
            title="Reward Earned!",
            message=message,
            metadata={"xp": xp_amount},
        )

    async def send_summary(
        self,
        user_id: str,
        title: str,
        summary: str,
    ) -> Notification:
        return await self.send(
            user_id=user_id,
            notification_type=NotificationType.SUMMARY,
            title=title,
            message=summary,
        )

    async def get_unread(self, user_id: str) -> list[Notification]:
        return await self.notification_repo.find_unread_by_user(user_id)

    async def mark_all_read(self, user_id: str) -> int:
        return await self.notification_repo.mark_all_read(user_id)
