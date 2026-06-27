"""Repository package with factory for dependency injection."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.calendar_event_repository import CalendarEventRepository
from app.repositories.daily_summary_repository import DailySummaryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.productivity_history_repository import ProductivityHistoryRepository
from app.repositories.reward_repository import RewardRepository
from app.repositories.subtask_repository import SubtaskRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository


class RepositoryContainer:
    """Container holding all repository instances for a database connection."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.users = UserRepository(db)
        self.tasks = TaskRepository(db)
        self.subtasks = SubtaskRepository(db)
        self.calendar_events = CalendarEventRepository(db)
        self.rewards = RewardRepository(db)
        self.notifications = NotificationRepository(db)
        self.daily_summaries = DailySummaryRepository(db)
        self.productivity_history = ProductivityHistoryRepository(db)


def get_repositories(db: AsyncIOMotorDatabase) -> RepositoryContainer:
    return RepositoryContainer(db)
