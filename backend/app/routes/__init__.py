"""Routes package."""

from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.dashboard import router as dashboard_router
from app.routes.tasks import router as tasks_router

__all__ = ["auth_router", "chat_router", "dashboard_router", "tasks_router"]
