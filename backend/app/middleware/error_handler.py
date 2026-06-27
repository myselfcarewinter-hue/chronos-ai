"""Authentication and error handling middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ChronosError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except NotFoundError as exc:
            return JSONResponse(status_code=404, content={"error": exc.message, "details": exc.details})
        except AuthenticationError as exc:
            return JSONResponse(status_code=401, content={"error": exc.message, "details": exc.details})
        except AuthorizationError as exc:
            return JSONResponse(status_code=403, content={"error": exc.message, "details": exc.details})
        except ValidationError as exc:
            return JSONResponse(status_code=422, content={"error": exc.message, "details": exc.details})
        except ChronosError as exc:
            logger.error("Chronos error: %s", exc.message)
            return JSONResponse(status_code=500, content={"error": exc.message, "details": exc.details})
        except Exception as exc:
            logger.exception("Unhandled error: %s", exc)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "details": {"type": type(exc).__name__}},
            )
