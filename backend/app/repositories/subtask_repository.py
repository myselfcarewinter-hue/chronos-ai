"""Subtask repository."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import Subtask, SubtaskStatus
from app.repositories.base_repository import BaseRepository


class SubtaskRepository(BaseRepository[Subtask]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "subtasks", Subtask)

    async def find_by_task(self, task_id: str) -> list[Subtask]:
        return await self.find_many({"task_id": task_id}, sort=[("order", 1)])

    async def find_incomplete_by_task(self, task_id: str) -> list[Subtask]:
        return await self.find_many(
            {
                "task_id": task_id,
                "status": {"$in": [SubtaskStatus.PENDING.value, SubtaskStatus.IN_PROGRESS.value]},
            },
            sort=[("order", 1)],
        )

    async def count_completed(self, task_id: str) -> int:
        return await self.count({"task_id": task_id, "status": SubtaskStatus.COMPLETED.value})
