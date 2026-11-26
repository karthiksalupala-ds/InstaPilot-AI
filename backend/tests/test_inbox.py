import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.api.v1.inbox import get_messaging_client
from app.core.crypto import encrypt_token
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.instagram import InstagramAccount, OAuthToken
from app.models.messaging import Conversation, Customer, Message
from app.models.tenant import User, WorkspaceMember
from app.services.instagram_messaging import MetaInstagramMessagingClient


async def test_meta_messaging_client_endpoints() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(200, json={"message_id": "mid.sent.1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MetaInstagramMessagingClient(http_client=http_client)
        await client.send_dm("17841400001", "cust_1", "Hello!", "tok")
        await client.send_private_reply("17841400001", "comment_1", "DM sent!", "tok")
        await client.reply_to_comment("comment_1", "Check your DMs!", "tok")

    assert seen_paths == [
        "/v21.0/17841400001/messages",
        "/v21.0/17841400001/messages",
        "/v21.0/comment_1/replies",
    ]


def test_manual_reply_blocked_when_24h_window_expired() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="op@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Operator",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="operator")
    account = InstagramAccount(
        id=acc_id,
        workspace_id=ws_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
    )
    cust = Customer(id=uuid.uuid4(), workspace_id=ws_id, instagram_account_id=acc_id, ig_scoped_user_id="c1")
    conv = Conversation(
        id=conv_id,
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        customer_id=cust.id,
        window_expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    tok = OAuthToken(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        encrypted_access_token=encrypt_token("ig_tok"),
        scopes=["instagram_business_manage_messages"],
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=50),
    )

    class _ExecResult:
        def first(self):
            return (conv, account, cust, tok)

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
            f"/api/v1/inbox/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
            json={"text": "Late reply"},
        )
        assert resp.status_code == 400
        assert "24-hour" in json.loads(resp.text)["detail"]
    finally:
        app.dependency_overrides.clear()


def test_approve_draft_sends_and_updates_status() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="op@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Operator",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="operator")
    account = InstagramAccount(
        id=acc_id,
        workspace_id=ws_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
    )
    cust = Customer(id=uuid.uuid4(), workspace_id=ws_id, instagram_account_id=acc_id, ig_scoped_user_id="c1")
    conv = Conversation(
        id=conv_id,
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        customer_id=cust.id,
        window_expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    tok = OAuthToken(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        encrypted_access_token=encrypt_token("ig_tok"),
        scopes=["instagram_business_manage_messages"],
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=50),
    )
    draft = Message(
        id=msg_id,
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        conversation_id=conv_id,
        sender_type="ai_agent",
        message_type="text",
        content="Initial draft",
        delivery_status="pending_approval",
        metadata_json={},
        created_at=datetime.now(UTC),
    )

    class _ExecResult:
        def first(self):
            return (conv, account, cust, tok)

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member, draft])
    mock_db.execute = AsyncMock(return_value=_ExecResult())

    async def _override_db():
        yield mock_db

    sent_texts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        sent_texts.append(body["message"]["text"])
        return httpx.Response(200, json={"message_id": "mid.sent.2"})

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_messaging_client] = lambda: MetaInstagramMessagingClient(
        http_client=mock_http
    )
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/inbox/conversations/{conv_id}/approve-draft",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
            json={"message_id": str(msg_id), "edited_text": "Edited & approved reply!"},
        )
        assert resp.status_code == 200
        assert draft.delivery_status == "sent"
        assert sent_texts == ["Edited & approved reply!"]
    finally:
        app.dependency_overrides.clear()
