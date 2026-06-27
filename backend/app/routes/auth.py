"""Authentication routes — Google OAuth."""

from fastapi import APIRouter, Depends, Query

from app.middleware.dependencies import get_oauth_service, get_repos
from app.repositories import RepositoryContainer
from app.routes.schemas import AuthCallbackResponse, AuthLoginResponse
from app.services.oauth_service import OAuthService
from app.database.models import User, UserPreferences, UserProfile, UserStats

router = APIRouter(prefix="/auth", tags=["Authentication"])

DEMO_GOOGLE_ID = "demo-google-id"
DEMO_EMAIL = "demo@chronos.ai"
DEMO_NAME = "Demo User"


@router.post("/login", response_model=AuthLoginResponse)
async def login(oauth: OAuthService = Depends(get_oauth_service)) -> AuthLoginResponse:
    """Return Google OAuth authorization URL."""
    url = oauth.get_authorization_url()
    return AuthLoginResponse(authorization_url=url)


@router.get("/callback", response_model=AuthCallbackResponse)
async def callback(
    code: str = Query(...),
    oauth: OAuthService = Depends(get_oauth_service),
) -> AuthCallbackResponse:
    """Handle Google OAuth callback and return JWT."""
    user, token = await oauth.handle_callback(code)
    return AuthCallbackResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "stats": user.stats.model_dump(),
        },
    )


@router.post("/demo", response_model=AuthCallbackResponse)
async def demo_login(
    repos: RepositoryContainer = Depends(get_repos),
    oauth: OAuthService = Depends(get_oauth_service),
) -> AuthCallbackResponse:
    """Create or retrieve a demo user and return a valid JWT.

    This allows the frontend demo mode to work with real API calls
    without requiring Google OAuth credentials.
    """
    existing = await repos.users.find_by_google_id(DEMO_GOOGLE_ID)

    if existing:
        user = existing
    else:
        user = await repos.users.create(
            User(
                google_id=DEMO_GOOGLE_ID,
                email=DEMO_EMAIL,
                name=DEMO_NAME,
                preferences=UserPreferences(),
                stats=UserStats(
                    total_tasks_completed=0,
                    total_xp=0,
                    current_streak=0,
                    longest_streak=0,
                    life_score=50.0,
                    level=1,
                ),
                profile=UserProfile(),
            )
        )

    token = oauth.create_access_token(user)

    return AuthCallbackResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "stats": user.stats.model_dump(),
        },
    )

