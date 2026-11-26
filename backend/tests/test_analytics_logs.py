import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.operations import AgentExecutionLog, Notification
from app.models.tenant import User, WorkspaceMember


def test_analytics_overview_returns_aggregated_kpis() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="viewer@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Viewer",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="viewer")

    mock_db = AsyncMock()
    # user, member, total_messages, ai_sent, pending, escalated, avg_latency, total_tokens, total_leads, converted
    mock_db.scalar = AsyncMock(
        side_effect=[user, member, 100, 72, 4, 8, 1250.5, 45000, 20, 5]
    )

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_messages"] == 100
        assert data["ai_sent_count"] == 72
        assert data["converted_leads"] == 5
        assert data["avg_latency_ms"] == 1250.5
    finally:
        app.dependency_overrides.clear()


def test_list_execution_logs_and_mark_notification_read() -> None:
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    notif_id = uuid.uuid4()

    user = User(
        id=user_id,
        email="op@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Operator",
        is_active=True,
    )
    member = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=user_id, role="operator")
    log_row = AgentExecutionLog(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        intent="pricing_question",
        retrieved_doc_ids=[],
        tools_called=[{"name": "search_products", "args": {"query": "hoodie"}}],
        draft_response="INR 1899",
        final_action="sent",
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        tokens_prompt=120,
        tokens_completion=45,
        latency_ms=890,
        created_at=datetime.now(UTC),
    )
    notif = Notification(
        id=notif_id,
        workspace_id=ws_id,
        type="escalation",
        title="Human Support Requested",
        body="Customer asked for manager",
        is_read=False,
        created_at=datetime.now(UTC),
    )

    class _ScalarsResult:
        def all(self):
            return [log_row]

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member, user, member, notif])
    mock_db.scalars = AsyncMock(return_value=_ScalarsResult())

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)

        logs_resp = client.get(
            "/api/v1/logs/agent-executions",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
        )
        assert logs_resp.status_code == 200
        assert logs_resp.json()[0]["final_action"] == "sent"

        notif_resp = client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": str(ws_id)},
        )
        assert notif_resp.status_code == 200
        assert notif_resp.json()["is_read"] is True
    finally:
        app.dependency_overrides.clear()
