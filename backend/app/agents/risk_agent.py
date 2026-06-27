"""Risk Prediction Agent — analyzes deadline failure probability."""

import logging
from datetime import datetime
from typing import Any

from app.agents.base_agent import BaseAgent
from app.database.models import RiskAnalysis, RiskLevel, User
from app.utils.helpers import clamp, utc_now

logger = logging.getLogger(__name__)

RISK_SCHEMA = """{
    "risk_percentage": "number 0-100",
    "risk_level": "low | medium | high | critical",
    "reason": "string — why this risk level",
    "suggestion": "string — actionable suggestion to reduce risk"
}"""


class RiskPredictionAgent(BaseAgent):
    """Predicts task failure probability based on multiple factors."""

    SYSTEM_INSTRUCTION = (
        "You are the Risk Prediction Agent for Chronos AI. "
        "Analyze task deadline risk considering time pressure, workload, "
        "calendar availability, and user productivity patterns. "
        "Be realistic and actionable."
    )

    async def execute(
        self,
        task_data: dict[str, Any],
        user: User,
        available_hours: float = 0.0,
        busy_hours: float = 0.0,
    ) -> RiskAnalysis:
        now = utc_now()
        deadline: datetime = task_data["deadline"]
        hours_until = max(0, (deadline - now).total_seconds() / 3600)
        estimated_hours = task_data.get("estimated_hours", 2.0)

        heuristic_risk = self._heuristic_risk(
            hours_until=hours_until,
            estimated_hours=estimated_hours,
            available_hours=available_hours,
            user=user,
            category=task_data.get("category", "general"),
        )

        prompt = f"""Analyze the failure risk for this task:

Task: {task_data.get('title')}
Category: {task_data.get('category')}
Difficulty: {task_data.get('difficulty')}
Estimated hours: {estimated_hours}
Deadline: {deadline.isoformat()}
Hours until deadline: {hours_until:.1f}
Available work hours before deadline: {available_hours:.1f}
Busy calendar hours: {busy_hours:.1f}

User productivity profile:
- Preferred work hours: {user.profile.preferred_work_hours}
- Average completion time by category: {user.profile.average_completion_time_by_category}
- Frequently delayed categories: {user.profile.frequently_delayed_categories}
- Typical weekly hours: {user.profile.typical_weekly_hours}
- Tasks completed: {user.stats.total_tasks_completed}
- Current streak: {user.stats.current_streak}

Heuristic baseline risk: {heuristic_risk:.0f}%

Provide your risk assessment as JSON."""

        try:
            result = await self._generate_json(prompt, RISK_SCHEMA)
            return RiskAnalysis(
                risk_percentage=clamp(float(result.get("risk_percentage", heuristic_risk))),
                risk_level=RiskLevel(result.get("risk_level", self._level_from_pct(heuristic_risk))),
                reason=str(result.get("reason", "Based on deadline proximity and workload")),
                suggestion=str(result.get("suggestion", "Start working on this task immediately")),
            )
        except Exception as exc:
            logger.warning("Risk Agent Gemini fallback: %s", exc)
            return RiskAnalysis(
                risk_percentage=heuristic_risk,
                risk_level=RiskLevel(self._level_from_pct(heuristic_risk)),
                reason=self._heuristic_reason(hours_until, estimated_hours, available_hours),
                suggestion="Begin working on this task as soon as possible to reduce risk.",
            )

    def _heuristic_risk(
        self,
        hours_until: float,
        estimated_hours: float,
        available_hours: float,
        user: User,
        category: str,
    ) -> float:
        if hours_until <= 0:
            return 95.0

        time_ratio = estimated_hours / max(hours_until, 0.1)
        base = min(time_ratio * 40, 60)

        if available_hours > 0 and estimated_hours > available_hours:
            base += 25

        if category in user.profile.frequently_delayed_categories:
            base += 15

        avg_time = user.profile.average_completion_time_by_category.get(category, 0)
        if avg_time > estimated_hours:
            base += 10

        return clamp(base)

    @staticmethod
    def _level_from_pct(pct: float) -> str:
        if pct >= 80:
            return "critical"
        if pct >= 60:
            return "high"
        if pct >= 35:
            return "medium"
        return "low"

    @staticmethod
    def _heuristic_reason(hours_until: float, estimated: float, available: float) -> str:
        if hours_until <= estimated:
            return f"Only {hours_until:.0f}h until deadline but task needs ~{estimated:.0f}h"
        if available > 0 and estimated > available:
            return f"Task needs {estimated:.0f}h but only {available:.0f}h available in calendar"
        return f"Moderate time pressure with {hours_until:.0f}h until deadline"
