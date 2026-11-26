import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.instagram import InstagramAccount
from app.models.messaging import Conversation, Customer, Message
from app.models.operations import AutomationRule, Lead
from app.models.tenant import User, WorkspaceMember
from app.services.automation_engine import evaluate_automation_rules
from app.services.instagram_messaging import MetaInstagramMessagingClient


async def test_automation_rule_comment_triggers_public_and_private_reply_and_lead() -> None:
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    account = InstagramAccount(
        id=acc_id,
        workspace_id=ws_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
    )
    customer = Customer(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        ig_scoped_user_id="cust_77",
    )
    conv = Conversation(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        customer_id=customer.id,
        channel="comment_thread",
        is_ai_paused=False,
    )
    msg = Message(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        conversation_id=conv.id,
        sender_type="customer",
        message_type="comment",
        content="Hey! PRICE please?",
        metadata_json={"comment_id": "comm_999"},
    )
    rule = AutomationRule(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        name="Price Comment Auto-DM",
        trigger_type="comment_received",
        conditions={"keywords": ["price"]},
        actions={
            "public_comment_reply": "Sent you the details in DM!",
            "private_reply_dm": "Hi! Here is our catalog link.",
            "create_lead_interest": "Hoodie Pricing",
            "pause_ai": True,
        },
        priority=10,
        is_enabled=True,
    )

    class _ScalarsResult:
        def all(self):
            return [rule]

    added: list[object] = []
    mock_db = AsyncMock()
    mock_db.scalars = AsyncMock(return_value=_ScalarsResult())
    mock_db.scalar = AsyncMock(return_value=None)  # No existing open lead
    mock_db.add = lambda obj: added.append(obj)

    called_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_urls.append(request.url.path)
        return httpx.Response(200, json={"id": "ok"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MetaInstagramMessagingClient(http_client=http_client)
        actions = await evaluate_automation_rules(
            db=mock_db,
            account=account,
            conversation=conv,
            customer=customer,
            message=msg,
            access_token="ig_tok",
            messaging_client=client,
        )

    assert len(actions) == 4
    assert "/v21.0/comm_999/replies" in called_urls
    assert "/v21.0/17841400001/messages" in called_urls
    assert any(isinstance(x, Lead) for x in added)
    assert conv.is_ai_paused is True


def test_create_lead_cross_workspace_blocked() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    cust_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="op@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Operator",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="operator")

    mock_db = AsyncMock()
    # user, member, account lookup returns None (foreign workspace)
    mock_db.scalar = AsyncMock(side_effect=[user, member, None])

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            "/api/v1/leads",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
            json={
                "instagram_account_id": str(acc_id),
                "customer_id": str(cust_id),
                "status": "new",
                "interest_category": "Skincare",
            },
        )
        assert resp.status_code == 404
        assert json.loads(resp.text)["detail"] == "Account not found"
    finally:
        app.dependency_overrides.clear()


def test_update_lead_status_and_followup() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="op@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Operator",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="operator")
    lead = Lead(
        id=lead_id,
        workspace_id=ws_id,
        instagram_account_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        status="new",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member, lead])

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.patch(
            f"/api/v1/leads/{lead_id}",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
            json={"status": "qualified", "notes": "Asked for bulk discount"},
        )
        assert resp.status_code == 200
        assert lead.status == "qualified"
        assert lead.notes == "Asked for bulk discount"
    finally:
        app.dependency_overrides.clear()
