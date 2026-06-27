"""Gamification service for XP, streaks, and rewards."""

import logging
import math

from app.config.settings import Settings, get_settings
from app.database.models import Reward, RewardType, User
from app.repositories.reward_repository import RewardRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class GamificationService:
    """Manages XP, streaks, levels, and life score."""

    def __init__(
        self,
        user_repo: UserRepository,
        reward_repo: RewardRepository,
        notification_service: NotificationService,
        settings: Settings | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.reward_repo = reward_repo
        self.notification_service = notification_service
        self.settings = settings or get_settings()

    async def award_task_completion(self, user: User, task_id: str, base_xp: int) -> User:
        """Award XP and update streak on task completion."""
        stats = user.stats.model_dump()
        multiplier = self.settings.streak_bonus_multiplier if stats["current_streak"] > 0 else 1.0
        xp_earned = int(base_xp * multiplier)

        stats["total_xp"] += xp_earned
        stats["total_tasks_completed"] += 1
        stats["current_streak"] += 1
        stats["longest_streak"] = max(stats["longest_streak"], stats["current_streak"])
        stats["level"] = self._calculate_level(stats["total_xp"])
        stats["life_score"] = self._calculate_life_score(stats)

        updated = await self.user_repo.update(user.id, {"stats": stats})
        user = updated or user

        reward = Reward(
            user_id=user.id,
            task_id=task_id,
            reward_type=RewardType.XP,
            amount=xp_earned,
            message=f"Earned {xp_earned} XP for completing a task!",
        )
        await self.reward_repo.create(reward)
        await self.notification_service.send_reward(user.id, reward.message, xp_earned)

        logger.info("User %s earned %d XP (streak: %d)", user.id, xp_earned, stats["current_streak"])
        return user

    async def reset_streak(self, user: User) -> User:
        stats = user.stats.model_dump()
        stats["current_streak"] = 0
        updated = await self.user_repo.update(user.id, {"stats": stats})
        return updated or user

    def _calculate_level(self, total_xp: int) -> int:
        return max(1, int(math.sqrt(total_xp / 100)) + 1)

    def _calculate_life_score(self, stats: dict) -> float:
        xp_component = min(stats["total_xp"] / 100, 50)
        streak_component = min(stats["current_streak"] * 2, 30)
        completion_component = min(stats["total_tasks_completed"], 20)
        return min(100.0, xp_component + streak_component + completion_component)
