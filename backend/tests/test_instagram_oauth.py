import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.instagram import get_oauth_client
from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.instagram import InstagramAccount, OAuthToken
from app.models.tenant import User, WorkspaceMember
from app.services.instagram_oauth import (
    MetaInstagramOAuthClient,
    create_oauth_state,
    verify_oauth_state,
)


def test_token_encryption_roundtrip_and_tamper_check() -> None:
    raw = "IGQVJ_test_secret_token_123"
    encrypted = encrypt_token(raw)
    assert encrypted.startswith("v1:")
    assert raw not in encrypted
    assert decrypt_token(encrypted) == raw

    with pytest.raises(ValueError):
        decrypt_token("v1:invalid-tampered-ciphertext")


def test_oauth_state_roundtrip() -> None:
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    state = create_oauth_state(ws_id, user_id)
    parsed_ws, parsed_user = verify_oauth_state(state)
    assert parsed_ws == ws_id
    assert parsed_user == user_id


async def test_meta_oauth_client_mock_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_LOGIN_CONFIG_ID", "")
    get_settings.cache_clear()
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "oauth/access_token" in url:
            return httpx.Response(200, json={"access_token": "short_tok", "user_id": 12345})
        if "/access_token" in url:
            return httpx.Response(
                200, json={"access_token": "long_tok_60d", "expires_in": 5183944}
            )
        if "/me" in url:
            return httpx.Response(
                200,
                json={"user_id": "17841400001", "username": "urbanthread", "account_type": "BUSINESS"},
            )
        if "/subscribed_apps" in url:
            return httpx.Response(200, json={"success": True})
        if "/refresh_access_token" in url:
            return httpx.Response(
                200, json={"access_token": "refreshed_tok", "expires_in": 5183944}
            )
        return httpx.Response(404, json={"error": "unexpected"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MetaInstagramOAuthClient(http_client=http_client)
        short = await client.exchange_code_for_short_token("auth_code_123")
        long_tok = await client.exchange_short_for_long_token(short["access_token"])
        profile = await client.fetch_profile(long_tok["access_token"])
        sub = await client.subscribe_webhooks(profile["user_id"], long_tok["access_token"])
        refreshed = await client.refresh_long_lived_token(long_tok["access_token"])

    assert long_tok["access_token"] == "long_tok_60d"
    assert profile["username"] == "urbanthread"
    assert sub["success"] is True
    assert refreshed["access_token"] == "refreshed_tok"


def test_refresh_token_enforces_24h_minimum_age() -> None:
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="owner@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Owner",
        is_active=True,
    )
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
    )
    account = InstagramAccount(
        id=account_id,
        workspace_id=workspace_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
        connection_status="connected",
        automation_mode="manual",
        is_agent_enabled=False,
        webhook_subscribed=True,
    )
    too_new_token = OAuthToken(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        instagram_account_id=account_id,
        encrypted_access_token=encrypt_token("old_tok"),
        token_type="long_lived",
        scopes=["instagram_business_basic"],
        issued_at=datetime.now(UTC) - timedelta(hours=2),
        expires_at=datetime.now(UTC) + timedelta(days=59),
    )

    class _ExecResult:
        def first(self):
            return (account, too_new_token)

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member])
    mock_db.execute = AsyncMock(return_value=_ExecResult())

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/instagram/accounts/{account_id}/refresh-token",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(workspace_id),
            },
        )
        assert resp.status_code == 400
        assert "24 hours" in json.loads(resp.text)["detail"]
    finally:
        app.dependency_overrides.clear()


def test_refresh_token_succeeds_after_24h() -> None:
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    account_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="owner@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Owner",
        is_active=True,
    )
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
    )
    account = InstagramAccount(
        id=account_id,
        workspace_id=workspace_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
        connection_status="connected",
        automation_mode="manual",
        is_agent_enabled=False,
        webhook_subscribed=True,
    )
    mature_token = OAuthToken(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        instagram_account_id=account_id,
        encrypted_access_token=encrypt_token("old_tok"),
        token_type="long_lived",
        scopes=["instagram_business_basic"],
        issued_at=datetime.now(UTC) - timedelta(days=50),
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )

    class _ExecResult:
        def first(self):
            return (account, mature_token)

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member])
    mock_db.execute = AsyncMock(return_value=_ExecResult())

    async def _override_db():
        yield mock_db

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "new_60d_tok", "expires_in": 5183944})

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_oauth_client] = lambda: MetaInstagramOAuthClient(http_client=mock_http)
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/instagram/accounts/{account_id}/refresh-token",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(workspace_id),
            },
        )
        assert resp.status_code == 200
        assert decrypt_token(mature_token.encrypted_access_token) == "new_60d_tok"
    finally:
        app.dependency_overrides.clear()
