"""Base agent class with shared interface."""

from abc import ABC, abstractmethod
from typing import Any

from app.services.gemini_service import GeminiService


class BaseAgent(ABC):
    """Abstract base for all Chronos AI agents."""

    SYSTEM_INSTRUCTION: str = "You are an AI agent in the Chronos AI productivity platform."

    def __init__(self, gemini_service: GeminiService) -> None:
        self.gemini = gemini_service

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's primary responsibility."""

    async def _generate_json(
        self,
        prompt: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any]:
        """Helper to call Gemini and get JSON — agents never call Gemini directly."""
        return await self.gemini.generate_json(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
            schema_hint=schema_hint,
        )

    async def _generate_text(self, prompt: str) -> str:
        return await self.gemini.generate_text(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
