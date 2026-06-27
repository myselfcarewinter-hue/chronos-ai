"""
Single shared Gemini API wrapper.

All agents MUST use this service — never call Gemini directly.
Uses the current google-genai SDK (v2.x).
"""

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.config.settings import Settings, get_settings
from app.utils.exceptions import GeminiServiceError

logger = logging.getLogger(__name__)


class GeminiService:
    """Centralized Google Gemini API service with singleton client."""

    _instance: "GeminiService | None" = None
    _initialized: bool = False

    def __new__(cls, settings: Settings | None = None) -> "GeminiService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if GeminiService._initialized:
            return

        self.settings = settings or get_settings()
        self._client: genai.Client | None = None
        self._configure()
        GeminiService._initialized = True

    def _configure(self) -> None:
        if not self.settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set — AI features will use fallback logic")
            return

        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        logger.info("Gemini service initialized with model: %s", self.settings.gemini_model)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Generate free-form text response."""
        if not self.is_available:
            raise GeminiServiceError("Gemini API not configured")

        try:
            config = genai_types.GenerateContentConfig(
                temperature=0.3,
                top_p=0.95,
                max_output_tokens=4096,
                system_instruction=system_instruction,
            )
            response = await self._client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=config,
            )
            text = response.text.strip() if response.text else ""
            logger.debug("Gemini text response length: %d", len(text))
            return text
        except Exception as exc:
            logger.error("Gemini text generation failed: %s", exc)
            raise GeminiServiceError(f"Text generation failed: {exc}") from exc

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
        schema_hint: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON response."""
        json_instruction = (
            "You MUST respond with valid JSON only. No markdown, no code fences, no explanation."
        )
        if schema_hint:
            json_instruction += f"\n\nExpected JSON schema:\n{schema_hint}"

        combined_system = json_instruction
        if system_instruction:
            combined_system = f"{system_instruction}\n\n{json_instruction}"

        text = await self.generate_text(prompt, combined_system)
        return self._parse_json_response(text)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_instruction: str | None = None,
    ) -> str:
        """Multi-turn chat conversation."""
        if not self.is_available:
            raise GeminiServiceError("Gemini API not configured")

        try:
            # Build contents list in google.genai format
            contents: list[genai_types.Content] = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=msg["content"])],
                    )
                )

            config = genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
            )
            response = await self._client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=config,
            )
            return response.text.strip() if response.text else ""
        except Exception as exc:
            logger.error("Gemini chat failed: %s", exc)
            raise GeminiServiceError(f"Chat failed: {exc}") from exc

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Extract and parse JSON from Gemini response."""
        cleaned = text.strip()

        # Remove markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            brace_match = re.search(r"\{[\s\S]*\}", cleaned)
            if brace_match:
                try:
                    return json.loads(brace_match.group())
                except json.JSONDecodeError:
                    pass

            logger.error("Failed to parse Gemini JSON response: %s", text[:500])
            raise GeminiServiceError("Failed to parse JSON response from Gemini")


def get_gemini_service(settings: Settings | None = None) -> GeminiService:
    """Factory for dependency injection."""
    return GeminiService(settings)
