"""Google OAuth 2.0 authentication service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.config.settings import Settings, get_settings
from app.database.models import User, UserPreferences, UserProfile, UserStats
from app.repositories.user_repository import UserRepository
from app.utils.exceptions import AuthenticationError, AuthorizationError
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class OAuthService:
    """Handles Google OAuth flow and JWT session tokens."""

    def __init__(
        self,
        user_repo: UserRepository,
        settings: Settings | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.settings = settings or get_settings()

    def get_authorization_url(self, state: str = "chronos") -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def handle_callback(self, code: str) -> tuple[User, str]:
        """Exchange auth code for tokens, create/update user, return JWT."""
        token_data = await self._exchange_code(code)
        user_info = await self._fetch_user_info(token_data["access_token"])
        user = await self._upsert_user(user_info, token_data)
        jwt_token = self.create_access_token(user)
        return user, jwt_token

    async def _exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

        if response.status_code != 200:
            logger.error("Token exchange failed: %s", response.text)
            raise AuthenticationError("Failed to exchange authorization code")

        return response.json()

    async def _fetch_user_info(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code != 200:
            raise AuthenticationError("Failed to fetch user info from Google")

        return response.json()

    async def _upsert_user(self, user_info: dict[str, Any], token_data: dict[str, Any]) -> User:
        existing = await self.user_repo.find_by_google_id(user_info["id"])
        expiry = utc_now() + timedelta(seconds=token_data.get("expires_in", 3600))

        if existing:
            updated = await self.user_repo.update(
                existing.id,
                {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token", existing.refresh_token),
                    "token_expiry": expiry,
                    "name": user_info.get("name", existing.name),
                    "avatar_url": user_info.get("picture", existing.avatar_url),
                },
            )
            return updated or existing

        new_user = User(
            google_id=user_info["id"],
            email=user_info["email"],
            name=user_info.get("name", user_info["email"]),
            avatar_url=user_info.get("picture"),
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=expiry,
            preferences=UserPreferences(),
            stats=UserStats(),
            profile=UserProfile(),
        )
        return await self.user_repo.create(new_user)

    def create_access_token(self, user: User) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.settings.jwt_expire_minutes)
        payload = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "exp": expire,
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise AuthorizationError("Invalid or expired token") from exc

    async def get_current_user(self, token: str) -> User:
        payload = self.decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthorizationError("Invalid token payload")

        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise AuthorizationError("User not found")

        return user

    async def refresh_google_token(self, user: User) -> User:
        """Refresh expired Google access token."""
        if not user.refresh_token:
            raise AuthenticationError("No refresh token available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": user.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            raise AuthenticationError("Failed to refresh Google token")

        token_data = response.json()
        expiry = utc_now() + timedelta(seconds=token_data.get("expires_in", 3600))

        updated = await self.user_repo.update(
            user.id,
            {
                "access_token": token_data["access_token"],
                "token_expiry": expiry,
            },
        )
        return updated or user
