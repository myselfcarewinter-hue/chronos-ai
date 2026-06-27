"""Calendar event repository."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import CalendarEvent
from app.repositories.base_repository import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "calendar_events", CalendarEvent)

    async def find_by_user(self, user_id: str, limit: int = 50) -> list[CalendarEvent]:
        return await self.find_many(
            {"user_id": user_id},
            limit=limit,
            sort=[("start_time", 1)],
        )

    async def find_by_task(self, task_id: str) -> list[CalendarEvent]:
        return await self.find_many({"task_id": task_id}, sort=[("start_time", 1)])

    async def find_by_google_event_id(self, google_event_id: str) -> CalendarEvent | None:
        document = await self.collection.find_one({"google_event_id": google_event_id})
        return self._to_model(document)
