"""Chat route — conversational AI assistant."""

from fastapi import APIRouter, Depends

from app.database.models import User
from app.middleware.dependencies import get_current_user, get_gemini, get_repos
from app.repositories import RepositoryContainer
from app.routes.schemas import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_SYSTEM_INSTRUCTION = """You are Chronos AI, an autonomous productivity companion.
You help users manage tasks, understand deadlines, stay motivated, and plan their work.
You have access to the user's task data and productivity stats provided in context.
Be concise, actionable, and encouraging. Suggest specific next steps when possible."""


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    gemini: GeminiService = Depends(get_gemini),
    repos: RepositoryContainer = Depends(get_repos),
) -> ChatResponse:
    """Chat with the Chronos AI assistant."""
    tasks = await repos.tasks.find_by_user(user.id, limit=10)
    task_context = "\n".join(
        f"- {t.title} (deadline: {t.deadline}, risk: {t.risk.risk_percentage:.0f}%, status: {t.status.value})"
        for t in tasks
    )

    context = f"""User: {user.name}
Level: {user.stats.level} | XP: {user.stats.total_xp} | Streak: {user.stats.current_streak} days
Life Score: {user.stats.life_score:.0f}/100

Active tasks:
{task_context or "No active tasks."}

Preferred work hours: {user.profile.preferred_work_hours}
Delayed categories: {user.profile.frequently_delayed_categories}"""

    messages = [{"role": "user", "content": context}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    try:
        reply = await gemini.chat(messages, system_instruction=CHAT_SYSTEM_INSTRUCTION)
    except Exception:
        reply = (
            "I'm having trouble connecting to my AI brain right now. "
            "Based on your stats, focus on your highest-priority task and "
            f"keep your {user.stats.current_streak}-day streak going!"
        )

    suggestions = _generate_suggestions(tasks, user)
    return ChatResponse(reply=reply, suggestions=suggestions)


def _generate_suggestions(tasks, user) -> list[str]:
    suggestions = []
    high_risk = [t for t in tasks if t.risk.risk_percentage >= 60]
    if high_risk:
        suggestions.append(f"Focus on '{high_risk[0].title}' — it's at high risk")
    if user.stats.current_streak == 0:
        suggestions.append("Complete a task today to start a new streak")
    if not tasks:
        suggestions.append("Tell me about a task you need to complete")
    if len(suggestions) < 3:
        suggestions.append("Show me my dashboard")
    return suggestions[:3]
