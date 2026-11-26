import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from arq.worker import create_worker
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.worker import WorkerSettings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Optionally run the ARQ background worker inside the API process ($0 single-instance mode)."""
    settings = get_settings()
    worker = None
    worker_task: asyncio.Task[None] | None = None

    if settings.enable_embedded_worker:
        try:
            worker = create_worker(WorkerSettings)  # type: ignore[arg-type]
            worker_task = asyncio.create_task(worker.async_run())
            logger.info("Embedded ARQ worker started")
        except (OSError, RuntimeError) as exc:
            logger.warning("Failed to start embedded ARQ worker: %s", exc)

    try:
        yield
    finally:
        if worker is not None:
            await worker.close()
        if worker_task is not None:
            worker_task.cancel()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
