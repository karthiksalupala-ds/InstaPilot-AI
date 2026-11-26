from typing import Any

import httpx
import redis.asyncio as aioredis

INSTAGRAM_GRAPH_API = "https://graph.instagram.com/v21.0"


async def check_account_rate_limit(
    redis_client: aioredis.Redis,
    ig_account_id: str,
    action: str = "send_dm",
    limit_per_hour: int = 700,
) -> bool:
    """Simple sliding-hour counter per Instagram account to respect Meta rate limits."""
    key = f"ratelimit:{action}:{ig_account_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 3600)
    return int(count) <= limit_per_hour


class MetaInstagramMessagingClient:
    """Official Meta Instagram Messaging & Comment Reply API client."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._external_client = http_client

    async def _post(self, url: str, **kwargs: Any) -> dict[str, Any]:
        if self._external_client is not None:
            resp = await self._external_client.post(url, **kwargs)
            resp.raise_for_status()
            return dict(resp.json())
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, **kwargs)
            resp.raise_for_status()
            return dict(resp.json())

    async def send_dm(
        self,
        ig_user_id: str,
        recipient_igsid: str,
        text: str,
        access_token: str,
    ) -> dict[str, Any]:
        """Send a standard Instagram DM within the 24-hour messaging window."""
        return await self._post(
            f"{INSTAGRAM_GRAPH_API}/{ig_user_id}/messages",
            params={"access_token": access_token},
            json={
                "recipient": {"id": recipient_igsid},
                "message": {"text": text},
            },
        )

    async def send_private_reply(
        self,
        ig_user_id: str,
        comment_id: str,
        text: str,
        access_token: str,
    ) -> dict[str, Any]:
        """Send a single Private Reply DM referencing a comment_id (7-day window)."""
        return await self._post(
            f"{INSTAGRAM_GRAPH_API}/{ig_user_id}/messages",
            params={"access_token": access_token},
            json={
                "recipient": {"comment_id": comment_id},
                "message": {"text": text},
            },
        )

    async def reply_to_comment(
        self,
        comment_id: str,
        text: str,
        access_token: str,
    ) -> dict[str, Any]:
        """Post a public reply to an Instagram comment."""
        return await self._post(
            f"{INSTAGRAM_GRAPH_API}/{comment_id}/replies",
            params={"access_token": access_token, "message": text},
        )
