"""Priority Agent — calculates task priority score."""

import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.database.models import PriorityAnalysis, PriorityLevel, RiskAnalysis, User
from app.utils.helpers import clamp

logger = logging.getLogger(__name__)

PRIORITY_SCHEMA = """{
    "priority_score": "number 0-100",
    "priority_level": "low | medium | high | urgent",
    "reason": "string — explanation of priority calculation"
}"""


class PriorityAgent(BaseAgent):
    """Calculates priority using urgency, importance, risk, and effort."""

    SYSTEM_INSTRUCTION = (
        "You are the Priority Agent for Chronos AI. "
        "Calculate task priority using urgency, importance, risk level, and effort. "
        "Higher urgency and risk = higher priority. More effort on urgent tasks = higher priority."
    )

    async def execute(
        self,
        task_data: dict[str, Any],
        risk: RiskAnalysis,
        user: User,
    ) -> PriorityAnalysis:
        urgency = self._calculate_urgency(task_data)
        importance = self._calculate_importance(task_data, user)
        risk_factor = risk.risk_percentage
        effort_factor = self._effort_factor(task_data.get("estimated_hours", 2.0))

        heuristic_score = (
            urgency * 0.35 + importance * 0.25 + risk_factor * 0.30 + effort_factor * 0.10
        )

        prompt = f"""Calculate priority for this task:

Title: {task_data.get('title')}
Category: {task_data.get('category')}
Difficulty: {task_data.get('difficulty')}
Estimated hours: {task_data.get('estimated_hours')}
Deadline: {task_data.get('deadline')}

Risk: {risk.risk_percentage:.0f}% ({risk.risk_level.value})
Risk reason: {risk.reason}

Computed factors:
- Urgency: {urgency:.0f}/100
- Importance: {importance:.0f}/100
- Risk factor: {risk_factor:.0f}/100
- Effort factor: {effort_factor:.0f}/100
- Heuristic score: {heuristic_score:.0f}/100

User context:
- Total tasks completed: {user.stats.total_tasks_completed}
- Life score: {user.stats.life_score}

Provide priority assessment as JSON."""

        try:
            result = await self._generate_json(prompt, PRIORITY_SCHEMA)
            score = clamp(float(result.get("priority_score", heuristic_score)))
            return PriorityAnalysis(
                priority_score=score,
                priority_level=PriorityLevel(
                    result.get("priority_level", self._level_from_score(score))
                ),
                reason=str(result.get("reason", "Calculated from urgency, risk, and importance")),
            )
        except Exception as exc:
            logger.warning("Priority Agent Gemini fallback: %s", exc)
            score = clamp(heuristic_score)
            return PriorityAnalysis(
                priority_score=score,
                priority_level=PriorityLevel(self._level_from_score(score)),
                reason=f"Urgency {urgency:.0f}, risk {risk_factor:.0f}, importance {importance:.0f}",
            )

    def _calculate_urgency(self, task_data: dict[str, Any]) -> float:
        from app.utils.helpers import utc_now

        deadline = task_data.get("deadline")
        if not deadline:
            return 30.0

        hours_until = max(0, (deadline - utc_now()).total_seconds() / 3600)
        if hours_until <= 24:
            return 95.0
        if hours_until <= 48:
            return 80.0
        if hours_until <= 72:
            return 65.0
        if hours_until <= 168:
            return 45.0
        return 20.0

    def _calculate_importance(self, task_data: dict[str, Any], user: User) -> float:
        category = task_data.get("category", "general")
        difficulty = task_data.get("difficulty", "medium")

        base = 50.0
        if category in ("academic", "work"):
            base += 20
        if difficulty in ("hard", "expert"):
            base += 15
        if category in user.profile.frequently_delayed_categories:
            base += 10

        return clamp(base)

    @staticmethod
    def _effort_factor(hours: float) -> float:
        if hours >= 8:
            return 80.0
        if hours >= 4:
            return 60.0
        if hours >= 2:
            return 40.0
        return 20.0

    @staticmethod
    def _level_from_score(score: float) -> str:
        if score >= 80:
            return "urgent"
        if score >= 60:
            return "high"
        if score >= 35:
            return "medium"
        return "low"
