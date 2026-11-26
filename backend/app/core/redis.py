import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings


def create_redis_client() -> aioredis.Redis:
    """Create an async Redis client from REDIS_URL."""
    return aioredis.from_url(get_settings().redis_url, decode_responses=True)


async def publish_workspace_event(
    redis_client: aioredis.Redis,
    workspace_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Publish a real-time event to a workspace's Redis Pub/Sub channel for SSE."""
    channel = f"workspace:{workspace_id}:events"
    message = json.dumps({"type": event_type, "payload": payload})
    await redis_client.publish(channel, message)
