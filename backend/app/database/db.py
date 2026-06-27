"""MongoDB async connection management using Motor."""

import logging
from typing import Any

# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Database:
    """Singleton-style database connection manager."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        cls.client = AsyncIOMotorClient(settings.mongo_uri)
        cls.db = cls.client[settings.mongo_db_name]
        await cls._ensure_indexes()
        logger.info("Connected to MongoDB: %s", settings.mongo_db_name)

    @classmethod
    async def disconnect(cls) -> None:
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            raise RuntimeError("Database not connected. Call Database.connect() first.")
        return cls.db

    @classmethod
    async def _ensure_indexes(cls) -> None:
        if cls.db is None:
            return

        # Users collection: separate unique indexes (recreated safely if conflicted)
        for field in ["google_id", "email"]:
            try:
                await cls.db["users"].create_index([(field, 1)], unique=True)
            except Exception:
                try:
                    await cls.db["users"].drop_index(f"{field}_1")
                    await cls.db["users"].create_index([(field, 1)], unique=True)
                except Exception as exc:
                    logger.warning("Could not recreate unique index for users.%s: %s", field, exc)

        # Compound indexes for query optimization
        await cls.db["tasks"].create_index([("user_id", 1), ("status", 1), ("deadline", 1)])
        await cls.db["tasks"].create_index([("user_id", 1), ("status", 1), ("risk.risk_percentage", -1)])
        await cls.db["subtasks"].create_index([("task_id", 1), ("status", 1)])
        await cls.db["calendar_events"].create_index([("user_id", 1), ("task_id", 1)])
        await cls.db["rewards"].create_index([("user_id", 1)])
        await cls.db["notifications"].create_index([("user_id", 1), ("read", 1)])
        await cls.db["daily_summaries"].create_index([("user_id", 1), ("date", -1)])
        await cls.db["productivity_history"].create_index([("user_id", 1), ("date", -1)])


def get_database() -> AsyncIOMotorDatabase:
    """Dependency injection helper for database access."""
    return Database.get_db()
