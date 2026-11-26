import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import get_settings

INSTAGRAM_OAUTH_AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
INSTAGRAM_OAUTH_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
INSTAGRAM_GRAPH_BASE = "https://graph.instagram.com"

FACEBOOK_OAUTH_AUTHORIZE_URL = "https://www.facebook.com/v21.0/dialog/oauth"
FACEBOOK_GRAPH_BASE = "https://graph.facebook.com/v21.0"

REQUIRED_SCOPES = [
    "instagram_business_basic",
    "instagram_business_manage_messages",
    "instagram_business_manage_comments",
]

WEBHOOK_FIELDS = [
    "messages",
    "message_reactions",
    "messaging_postbacks",
    "messaging_referral",
    "messaging_seen",
    "comments",
]


def create_oauth_state(workspace_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Create a short-lived signed JWT for Meta OAuth CSRF/state validation."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "nonce": uuid.uuid4().hex,
        "purpose": "ig_oauth",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def verify_oauth_state(state: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Verify signed OAuth state and return (workspace_id, user_id)."""
    settings = get_settings()
    payload = jwt.decode(state, settings.jwt_secret_key, algorithms=["HS256"])
    if payload.get("purpose") != "ig_oauth":
        raise ValueError("Invalid OAuth state purpose")
    return uuid.UUID(str(payload["workspace_id"])), uuid.UUID(str(payload["user_id"]))


def build_authorize_url(workspace_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Construct Meta Unified Login (when META_LOGIN_CONFIG_ID is set) or Instagram Login URL."""
    settings = get_settings()
    state = create_oauth_state(workspace_id, user_id)

    if settings.meta_login_config_id:
        params = {
            "client_id": settings.meta_app_id,
            "config_id": settings.meta_login_config_id,
            "redirect_uri": settings.meta_redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{FACEBOOK_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    params = {
        "enable_fb_login": "0",
        "force_authentication": "1",
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "response_type": "code",
        "scope": ",".join(REQUIRED_SCOPES),
        "state": state,
    }
    return f"{INSTAGRAM_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


class MetaInstagramOAuthClient:
    """Async client for Meta Instagram Login & Unified Login OAuth endpoints."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._external_client = http_client

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        if self._external_client is not None:
            resp = await self._external_client.request(method, url, **kwargs)
            resp.raise_for_status()
            return dict(resp.json())
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return dict(resp.json())

    async def exchange_code_for_short_token(self, code: str) -> dict[str, Any]:
        settings = get_settings()
        if settings.meta_login_config_id:
            return await self._request(
                "GET",
                f"{FACEBOOK_GRAPH_BASE}/oauth/access_token",
                params={
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "redirect_uri": settings.meta_redirect_uri,
                    "code": code,
                },
            )
        return await self._request(
            "POST",
            INSTAGRAM_OAUTH_TOKEN_URL,
            data={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": settings.meta_redirect_uri,
                "code": code,
            },
        )

    async def exchange_short_for_long_token(self, short_token: str) -> dict[str, Any]:
        settings = get_settings()
        if settings.meta_login_config_id:
            return await self._request(
                "GET",
                f"{FACEBOOK_GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret,
                    "fb_exchange_token": short_token,
                },
            )
        return await self._request(
            "GET",
            f"{INSTAGRAM_GRAPH_BASE}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.meta_app_secret,
                "access_token": short_token,
            },
        )

    async def refresh_long_lived_token(self, long_token: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"{INSTAGRAM_GRAPH_BASE}/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": long_token,
            },
        )

    async def fetch_profile(self, access_token: str) -> dict[str, Any]:
        settings = get_settings()
        if settings.meta_login_config_id:
            pages = await self._request(
                "GET",
                f"{FACEBOOK_GRAPH_BASE}/me/accounts",
                params={
                    "fields": "instagram_business_account{id,username,profile_picture_url}",
                    "access_token": access_token,
                },
            )
            for page in pages.get("data", []):
                ig = page.get("instagram_business_account")
                if ig and ig.get("id"):
                    return {
                        "user_id": str(ig["id"]),
                        "username": str(ig.get("username", ig["id"])),
                        "account_type": "BUSINESS",
                        "profile_picture_url": ig.get("profile_picture_url"),
                    }
            raise ValueError("No Instagram Business account linked to this Facebook Page")

        return await self._request(
            "GET",
            f"{INSTAGRAM_GRAPH_BASE}/me",
            params={
                "fields": "user_id,username,account_type,profile_picture_url",
                "access_token": access_token,
            },
        )

    async def subscribe_webhooks(self, ig_user_id: str, access_token: str) -> dict[str, Any]:
        settings = get_settings()
        base = FACEBOOK_GRAPH_BASE if settings.meta_login_config_id else INSTAGRAM_GRAPH_BASE
        return await self._request(
            "POST",
            f"{base}/{ig_user_id}/subscribed_apps",
            params={
                "subscribed_fields": ",".join(WEBHOOK_FIELDS),
                "access_token": access_token,
            },
        )
