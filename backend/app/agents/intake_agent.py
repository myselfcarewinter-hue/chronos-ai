"""Intake Agent — parses natural language into structured task data."""

import logging
from datetime import datetime, timedelta
from typing import Any

from app.agents.base_agent import BaseAgent
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

INTAKE_SCHEMA = """{
    "title": "string — concise task title",
    "deadline": "ISO 8601 datetime string or null",
    "category": "string — e.g. academic, work, personal, health, finance",
    "difficulty": "string — easy, medium, hard, expert",
    "estimated_hours": "number — estimated hours to complete",
    "location": "string or null — optional location",
    "description": "string — expanded description of the task"
}"""


class IntakeAgent(BaseAgent):
    """Parses natural language task input into structured JSON."""

    SYSTEM_INSTRUCTION = (
        "You are the Intake Agent for Chronos AI. "
        "Parse natural language task descriptions into structured data. "
        "Infer reasonable defaults when information is missing. "
        "Current datetime for reference: use the provided context."
    )

    async def execute(self, raw_input: str, user_timezone: str = "UTC") -> dict[str, Any]:
        now = utc_now()
        prompt = f"""Parse this task into structured JSON.

User input: "{raw_input}"
Current datetime (UTC): {now.isoformat()}
User timezone: {user_timezone}

Rules:
- If a relative deadline is mentioned (e.g. "Friday night", "next week"), calculate the actual datetime.
- Estimate hours based on task complexity and type.
- Category should reflect the domain of work.
- Difficulty should reflect cognitive and time demands."""

        try:
            result = await self._generate_json(prompt, INTAKE_SCHEMA)
            return self._validate_and_normalize(result, now)
        except Exception as exc:
            logger.warning("Intake Agent Gemini fallback: %s", exc)
            return self._fallback_parse(raw_input, now)

    def _validate_and_normalize(self, data: dict[str, Any], now: datetime) -> dict[str, Any]:
        deadline = data.get("deadline")
        if isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except ValueError:
                deadline = now + timedelta(days=7)
        elif deadline is None:
            deadline = now + timedelta(days=7)

        return {
            "title": str(data.get("title", "Untitled Task"))[:200],
            "deadline": deadline,
            "category": str(data.get("category", "general")).lower(),
            "difficulty": str(data.get("difficulty", "medium")).lower(),
            "estimated_hours": max(0.5, float(data.get("estimated_hours", 2.0))),
            "location": data.get("location"),
            "description": str(data.get("description", "")),
        }

    def _fallback_parse(self, raw_input: str, now: datetime) -> dict[str, Any]:
        """Rule-based fallback when Gemini is unavailable."""
        title = raw_input[:100].strip()
        if len(raw_input) > 100:
            title = title.rsplit(" ", 1)[0] + "..."

        deadline = now + timedelta(days=7)
        lower = raw_input.lower()
        if "friday" in lower:
            days_ahead = (4 - now.weekday()) % 7 or 7
            deadline = now + timedelta(days=days_ahead)
            deadline = deadline.replace(hour=23, minute=59)
        elif "tomorrow" in lower:
            deadline = now + timedelta(days=1)
        elif "tonight" in lower:
            deadline = now.replace(hour=23, minute=59)

        hours = 2.0
        if any(w in lower for w in ["assignment", "project", "thesis", "report"]):
            hours = 8.0
        elif any(w in lower for w in ["email", "call", "quick"]):
            hours = 0.5

        difficulty = "medium"
        if any(w in lower for w in ["complex", "advanced", "thesis", "dissertation"]):
            difficulty = "hard"
        elif any(w in lower for w in ["quick", "simple", "easy"]):
            difficulty = "easy"

        category = "general"
        if any(w in lower for w in ["assignment", "exam", "study", "homework", "ml", "class"]):
            category = "academic"
        elif any(w in lower for w in ["meeting", "deadline", "client", "report"]):
            category = "work"

        return {
            "title": title,
            "deadline": deadline,
            "category": category,
            "difficulty": difficulty,
            "estimated_hours": hours,
            "location": None,
            "description": raw_input,
        }
