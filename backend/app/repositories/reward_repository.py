"""Reward repository."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import Reward
from app.repositories.base_repository import BaseRepository


class RewardRepository(BaseRepository[Reward]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "rewards", Reward)

    async def find_by_user(self, user_id: str, limit: int = 50) -> list[Reward]:
        return await self.find_many({"user_id": user_id}, limit=limit, sort=[("created_at", -1)])
