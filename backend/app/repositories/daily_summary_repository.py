"""Daily summary repository."""

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import DailySummary
from app.repositories.base_repository import BaseRepository


class DailySummaryRepository(BaseRepository[DailySummary]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "daily_summaries", DailySummary)

    async def find_by_user_and_date(self, user_id: str, date: datetime) -> DailySummary | None:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        document = await self.collection.find_one(
            {"user_id": user_id, "date": {"$gte": start, "$lte": end}}
        )
        return self._to_model(document)

    async def find_recent(self, user_id: str, limit: int = 7) -> list[DailySummary]:
        return await self.find_many(
            {"user_id": user_id},
            limit=limit,
            sort=[("date", -1)],
        )
