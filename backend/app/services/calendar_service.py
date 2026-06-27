"""Google Calendar integration service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config.settings import Settings, get_settings
from app.database.models import CalendarEvent, User
from app.repositories.calendar_event_repository import CalendarEventRepository
from app.services.oauth_service import OAuthService
from app.utils.exceptions import CalendarServiceError
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class CalendarService:
    """Manages Google Calendar event creation and synchronization."""

    def __init__(
        self,
        calendar_repo: CalendarEventRepository,
        oauth_service: OAuthService,
        settings: Settings | None = None,
    ) -> None:
        self.calendar_repo = calendar_repo
        self.oauth_service = oauth_service
        self.settings = settings or get_settings()

    def _build_credentials(self, user: User) -> Credentials:
        if not user.access_token:
            raise CalendarServiceError("User has no Google access token")

        return Credentials(
            token=user.access_token,
            refresh_token=user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
        )

    async def _ensure_valid_token(self, user: User) -> User:
        if user.token_expiry and user.token_expiry <= utc_now():
            return await self.oauth_service.refresh_google_token(user)
        return user

    async def get_free_busy(
        self,
        user: User,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return busy time blocks from Google Calendar.

        Returns an empty list if the user has no Google token or if the
        Calendar API call fails — callers must handle the graceful fallback.
        """
        if not user.access_token:
            logger.debug("get_free_busy: user %s has no access token — returning empty", user.id)
            return []

        try:
            user = await self._ensure_valid_token(user)
            service = await asyncio.to_thread(build, "calendar", "v3", credentials=self._build_credentials(user))
            body = {
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": "primary"}],
            }
            query = service.freebusy().query(body=body)
            result = await asyncio.to_thread(query.execute)
            busy_slots = result.get("calendars", {}).get("primary", {}).get("busy", [])
            return busy_slots
        except HttpError as exc:
            logger.error("Free/busy query failed: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Free/busy unexpected error: %s — returning empty", exc)
            return []

    async def create_event(
        self,
        user: User,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str | None = None,
        task_id: str | None = None,
        subtask_id: str | None = None,
    ) -> CalendarEvent:
        """Create a Google Calendar event and store locally.

        Always stores the event locally. Google Calendar sync only runs when
        the user has a valid access token.
        """
        google_event_id: str | None = None

        if user.access_token:
            try:
                user = await self._ensure_valid_token(user)
                service = await asyncio.to_thread(build, "calendar", "v3", credentials=self._build_credentials(user))
                event_body: dict[str, Any] = {
                    "summary": title,
                    "description": description,
                    "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
                    "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
                }
                if location:
                    event_body["location"] = location

                insert_request = service.events().insert(calendarId="primary", body=event_body)
                google_event = await asyncio.to_thread(insert_request.execute)
                google_event_id = google_event.get("id")
                logger.info("Created Google Calendar event: %s", google_event_id)
            except HttpError as exc:
                logger.warning("Google Calendar event creation failed: %s — storing locally only", exc)
            except Exception as exc:
                logger.warning("Google Calendar sync error: %s — storing locally only", exc)
        else:
            logger.debug("create_event: no access token for user %s — storing locally only", user.id)

        calendar_event = CalendarEvent(
            user_id=user.id,
            task_id=task_id or "",
            subtask_id=subtask_id,
            google_event_id=google_event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            synced=google_event_id is not None,
        )
        return await self.calendar_repo.create(calendar_event)

    async def delete_event(self, user: User, calendar_event: CalendarEvent) -> bool:
        """Delete event from Google Calendar and local store."""
        if calendar_event.google_event_id:
            user = await self._ensure_valid_token(user)
            try:
                service = await asyncio.to_thread(build, "calendar", "v3", credentials=self._build_credentials(user))
                delete_request = service.events().delete(
                    calendarId="primary",
                    eventId=calendar_event.google_event_id,
                )
                await asyncio.to_thread(delete_request.execute)
            except HttpError as exc:
                logger.warning("Failed to delete Google event: %s", exc)

        return await self.calendar_repo.delete(calendar_event.id)

    async def get_upcoming_events(
        self,
        user: User,
        days: int = 7,
    ) -> list[CalendarEvent]:
        """Get upcoming calendar events for a user."""
        return await self.calendar_repo.find_by_user(user.id, limit=days * 5)

    async def find_available_slots(
        self,
        user: User,
        duration_hours: float,
        start: datetime,
        end: datetime,
        preferred_hours: list[int] | None = None,
    ) -> list[tuple[datetime, datetime]]:
        """Find available time slots considering calendar busy times."""
        busy_slots = await self.get_free_busy(user, start, end)
        preferred = preferred_hours or list(range(9, 18))
        duration = timedelta(hours=duration_hours)
        available: list[tuple[datetime, datetime]] = []

        current = start.replace(minute=0, second=0, microsecond=0)
        if current < start:
            current += timedelta(hours=1)

        while current + duration <= end and len(available) < 10:
            if current.hour in preferred:
                slot_end = current + duration
                is_busy = any(
                    self._slots_overlap(
                        current,
                        slot_end,
                        datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                        datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
                    )
                    for b in busy_slots
                )
                if not is_busy:
                    available.append((current, slot_end))
            current += timedelta(hours=1)

        return available

    @staticmethod
    def _slots_overlap(
        start_a: datetime,
        end_a: datetime,
        start_b: datetime,
        end_b: datetime,
    ) -> bool:
        return start_a < end_b and end_a > start_b
