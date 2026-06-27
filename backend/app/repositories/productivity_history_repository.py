"""Productivity history repository."""

from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import ProductivityHistory
from app.repositories.base_repository import BaseRepository
from app.utils.helpers import utc_now


class ProductivityHistoryRepository(BaseRepository[ProductivityHistory]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "productivity_history", ProductivityHistory)

    async def find_by_date_range(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
    ) -> list[ProductivityHistory]:
        return await self.find_many(
            {"user_id": user_id, "date": {"$gte": start, "$lte": end}},
            limit=365,
            sort=[("date", 1)],
        )

    async def find_last_n_days(self, user_id: str, days: int = 30) -> list[ProductivityHistory]:
        end = utc_now()
        start = end - timedelta(days=days)
        return await self.find_by_date_range(user_id, start, end)

