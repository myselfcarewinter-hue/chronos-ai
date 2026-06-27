"""User repository."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "users", User)

    async def find_by_google_id(self, google_id: str) -> User | None:
        document = await self.collection.find_one({"google_id": google_id})
        return self._to_model(document)

    async def find_by_email(self, email: str) -> User | None:
        document = await self.collection.find_one({"email": email})
        return self._to_model(document)

    async def update_stats(self, user_id: str, stats_updates: dict) -> User | None:
        return await self.update(user_id, {"stats": stats_updates})

    async def update_profile(self, user_id: str, profile_data: dict) -> User | None:
        return await self.update(user_id, {"profile": profile_data})
