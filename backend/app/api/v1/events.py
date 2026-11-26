import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import require_workspace_role
from app.core.redis import create_redis_client
from app.models.tenant import WorkspaceMember

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def stream_workspace_events(
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
) -> StreamingResponse:
    """Stream real-time workspace events (new messages, approvals, alerts) over SSE."""
    channel = f"workspace:{caller.workspace_id}:events"

    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = create_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield 'data: {"type": "connected"}\n\n'
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg and msg.get("data"):
                    yield f"data: {msg['data']}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.05)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
