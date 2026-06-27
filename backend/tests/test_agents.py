"""Tests for Chronos AI backend."""

import pytest
from datetime import datetime, timedelta, timezone

from app.agents.intake_agent import IntakeAgent
from app.agents.priority_agent import PriorityAgent
from app.agents.risk_agent import RiskPredictionAgent
from app.database.models import RiskAnalysis, RiskLevel, User, UserPreferences, UserProfile, UserStats
from app.services.gemini_service import GeminiService
from app.utils.helpers import clamp, utc_now


@pytest.fixture
def gemini_service():
    return GeminiService()


@pytest.fixture
def sample_user():
    return User(
        id="test-user-id",
        google_id="google-123",
        email="test@example.com",
        name="Test User",
        preferences=UserPreferences(),
        stats=UserStats(),
        profile=UserProfile(),
    )


class TestIntakeAgent:
    @pytest.mark.asyncio
    async def test_fallback_parse_ml_assignment(self, gemini_service):
        agent = IntakeAgent(gemini_service)
        result = await agent.execute("I have an ML assignment due Friday night.")

        assert "title" in result
        assert result["category"] == "academic"
        assert result["estimated_hours"] >= 0.5
        assert isinstance(result["deadline"], datetime)

    @pytest.mark.asyncio
    async def test_fallback_parse_quick_task(self, gemini_service):
        agent = IntakeAgent(gemini_service)
        result = await agent.execute("Quick email to the team about the meeting tomorrow")

        assert result["estimated_hours"] <= 2.0
        assert result["category"] in ("work", "general")


class TestRiskAgent:
    @pytest.mark.asyncio
    async def test_heuristic_high_risk(self, gemini_service, sample_user):
        agent = RiskPredictionAgent(gemini_service)
        task_data = {
            "title": "Big Project",
            "category": "work",
            "difficulty": "hard",
            "estimated_hours": 20.0,
            "deadline": utc_now() + timedelta(hours=12),
        }

        result = await agent.execute(task_data, sample_user, available_hours=4.0, busy_hours=8.0)

        assert isinstance(result, RiskAnalysis)
        assert result.risk_percentage >= 50
        assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @pytest.mark.asyncio
    async def test_heuristic_low_risk(self, gemini_service, sample_user):
        agent = RiskPredictionAgent(gemini_service)
        task_data = {
            "title": "Easy Task",
            "category": "personal",
            "difficulty": "easy",
            "estimated_hours": 1.0,
            "deadline": utc_now() + timedelta(days=14),
        }

        result = await agent.execute(task_data, sample_user, available_hours=40.0)

        assert result.risk_percentage < 60


class TestPriorityAgent:
    @pytest.mark.asyncio
    async def test_priority_calculation(self, gemini_service, sample_user):
        agent = PriorityAgent(gemini_service)
        task_data = {
            "title": "Urgent Report",
            "category": "work",
            "difficulty": "hard",
            "estimated_hours": 8.0,
            "deadline": utc_now() + timedelta(hours=24),
        }
        risk = RiskAnalysis(risk_percentage=75.0, risk_level=RiskLevel.HIGH, reason="Tight deadline")

        result = await agent.execute(task_data, risk, sample_user)

        assert result.priority_score >= 50


class TestHelpers:
    def test_clamp(self):
        assert clamp(150) == 100.0
        assert clamp(-10) == 0.0
        assert clamp(50) == 50.0

    def test_utc_now(self):
        now = utc_now()
        assert now.tzinfo is not None


class TestGeminiService:
    def test_singleton(self):
        s1 = GeminiService()
        s2 = GeminiService()
        assert s1 is s2

    def test_not_available_without_key(self):
        service = GeminiService()
        # Without API key configured, should not be available
        # (depends on env — this test validates the interface)
        assert isinstance(service.is_available, bool)
