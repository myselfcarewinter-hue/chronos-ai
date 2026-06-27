"""Task repository."""

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.models import Task, TaskStatus
from app.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "tasks", Task)

    async def find_by_user(
        self,
        user_id: str,
        status: TaskStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        query: dict = {"user_id": user_id}
        if status:
            query["status"] = status.value
        return await self.find_many(query, skip=skip, limit=limit, sort=[("deadline", 1)])

    async def find_upcoming_deadlines(self, user_id: str, before: datetime) -> list[Task]:
        return await self.find_many(
            {
                "user_id": user_id,
                "status": {"$in": [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]},
                "deadline": {"$lte": before, "$ne": None},
            },
            sort=[("deadline", 1)],
        )

    async def find_overdue(self, user_id: str, now: datetime) -> list[Task]:
        return await self.find_many(
            {
                "user_id": user_id,
                "status": {"$in": [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]},
                "deadline": {"$lt": now},
            },
            sort=[("deadline", 1)],
        )

    async def find_high_risk(self, user_id: str, threshold: float = 70.0) -> list[Task]:
        return await self.find_many(
            {
                "user_id": user_id,
                "status": {"$in": [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]},
                "risk.risk_percentage": {"$gte": threshold},
            },
            sort=[("risk.risk_percentage", -1)],
        )

    async def find_due_today(self, user_id: str, start: datetime, end: datetime) -> list[Task]:
        return await self.find_many(
            {
                "user_id": user_id,
                "status": {"$in": [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]},
                "deadline": {"$gte": start, "$lte": end},
            },
            sort=[("priority.priority_score", -1)],
        )
