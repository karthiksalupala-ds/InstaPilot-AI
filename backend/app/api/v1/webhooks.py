import hashlib
import hmac
import json
from collections.abc import AsyncGenerator
from dataclasses import asdict
from typing import Any

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.core.config import get_settings
from app.core.redis import create_redis_client
from app.services.webhook_processor import extract_normalized_events

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = create_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def get_arq_pool() -> AsyncGenerator[ArqRedis, None]:
    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        yield pool
    finally:
        await pool.aclose()


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verify Meta X-Hub-Signature-256 HMAC-SHA256 header in constant time."""
    if not signature_header or not signature_header.startswith("sha256=") or not app_secret:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.get("/instagram")
async def verify_instagram_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """Handle Meta webhook verification handshake."""
    settings = get_settings()
    if (
        hub_mode != "subscribe"
        or not settings.meta_verify_token
        or not hmac.compare_digest(hub_verify_token, settings.meta_verify_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")
    return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)


@router.post("/instagram", status_code=status.HTTP_200_OK)
async def receive_instagram_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    redis_client: aioredis.Redis = Depends(get_redis),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> dict[str, Any]:
    """Verify signature, deduplicate events in Redis, enqueue to ARQ, and return 200 fast."""
    raw_body = await request.body()
    settings = get_settings()
    if not verify_meta_signature(raw_body, x_hub_signature_256, settings.meta_app_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    payload = json.loads(raw_body.decode("utf-8"))
    events = extract_normalized_events(payload)

    enqueued = 0
    for event in events:
        dedup_key = f"dedup:ig:{event.ig_account_user_id}:{event.external_event_id}"
        is_new = await redis_client.set(dedup_key, "1", ex=86400, nx=True)
        if not is_new:
            continue
        await arq_pool.enqueue_job("process_instagram_event", asdict(event))
        enqueued += 1

    return {"status": "accepted", "enqueued": enqueued}
