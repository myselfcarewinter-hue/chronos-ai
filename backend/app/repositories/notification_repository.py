"""Notification repository."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "notifications", Notification)

    async def find_unread_by_user(self, user_id: str, limit: int = 50) -> list[Notification]:
        return await self.find_many(
            {"user_id": user_id, "read": False},
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def mark_all_read(self, user_id: str) -> int:
        result = await self.collection.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count
