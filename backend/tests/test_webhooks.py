import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.v1.webhooks import get_arq_pool, get_redis
from app.core.config import get_settings
from app.main import app
from app.models.instagram import InstagramAccount
from app.services.webhook_processor import (
    NormalizedWebhookEvent,
    extract_normalized_events,
    ingest_instagram_event,
)


def _sign_payload(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_webhook_challenge_verification(monkeypatch) -> None:
    monkeypatch.setenv("META_VERIFY_TOKEN", "test_verify_token")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        ok = client.get(
            "/api/v1/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "99887766",
            },
        )
        assert ok.status_code == 200
        assert ok.text == "99887766"

        bad = client.get(
            "/api/v1/webhooks/instagram",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "99887766",
            },
        )
        assert bad.status_code == 403
    finally:
        get_settings.cache_clear()


def test_webhook_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("META_APP_SECRET", "super_secret_app")
    get_settings.cache_clear()
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_arq_pool] = lambda: AsyncMock()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/webhooks/instagram",
            content=b'{"object":"instagram","entry":[]}',
            headers={"X-Hub-Signature-256": "sha256=deadbeef"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_webhook_accepts_and_deduplicates(monkeypatch) -> None:
    monkeypatch.setenv("META_APP_SECRET", "super_secret_app")
    get_settings.cache_clear()

    seen_keys: set[str] = set()
    mock_redis = AsyncMock()

    async def _fake_set(key: str, val: str, ex: int = 86400, nx: bool = True) -> bool:
        if nx and key in seen_keys:
            return False
        seen_keys.add(key)
        return True

    mock_redis.set = AsyncMock(side_effect=_fake_set)
    mock_arq = AsyncMock()

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_arq_pool] = lambda: mock_arq
    try:
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "17841400001",
                    "messaging": [
                        {
                            "sender": {"id": "cust_1"},
                            "recipient": {"id": "17841400001"},
                            "timestamp": 1700000000,
                            "message": {"mid": "mid.123", "text": "Price please?"},
                        }
                    ],
                }
            ],
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = _sign_payload(raw, "super_secret_app")

        client = TestClient(app)
        first = client.post(
            "/api/v1/webhooks/instagram",
            content=raw,
            headers={"X-Hub-Signature-256": sig},
        )
        second = client.post(
            "/api/v1/webhooks/instagram",
            content=raw,
            headers={"X-Hub-Signature-256": sig},
        )

        assert first.status_code == 200
        assert first.json()["enqueued"] == 1
        assert second.status_code == 200
        assert second.json()["enqueued"] == 0
        assert mock_arq.enqueue_job.await_count == 1
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_extract_dm_and_comment_events() -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "17841400001",
                "messaging": [
                    {
                        "sender": {"id": "cust_1"},
                        "recipient": {"id": "17841400001"},
                        "message": {"mid": "m1", "text": "Hi!"},
                    },
                    {
                        "sender": {"id": "17841400001"},
                        "recipient": {"id": "cust_1"},
                        "message": {"mid": "m_echo", "text": "Echo", "is_echo": True},
                    },
                ],
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "c_99",
                            "text": "Price?",
                            "from": {"id": "cust_2", "username": "rohan_m"},
                            "media": {"id": "med_1"},
                        },
                    }
                ],
            }
        ],
    }
    events = extract_normalized_events(payload)
    assert len(events) == 2
    assert events[0].channel == "dm"
    assert events[0].external_event_id == "m1"
    assert events[1].channel == "comment_thread"
    assert events[1].external_event_id == "comment:c_99"


async def test_ingest_event_sets_24h_window_and_publishes_sse() -> None:
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    account = InstagramAccount(
        id=acc_id,
        workspace_id=ws_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
        connection_status="connected",
        automation_mode="manual",
        is_agent_enabled=False,
        webhook_subscribed=True,
    )

    added_objects: list[object] = []
    mock_db = AsyncMock()
    # account lookup -> existing_msg (None) -> customer (None) -> conversation (None)
    mock_db.scalar = AsyncMock(side_effect=[account, None, None, None])

    def _add(obj: object) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        added_objects.append(obj)

    mock_db.add = _add
    mock_redis = AsyncMock()

    event = NormalizedWebhookEvent(
        ig_account_user_id="17841400001",
        external_event_id="mid.999",
        sender_ig_id="cust_99",
        sender_username=None,
        channel="dm",
        message_type="text",
        content="Do you have black hoodies?",
        media_url=None,
        metadata={},
    )
    msg = await ingest_instagram_event(mock_db, mock_redis, event)
    assert msg is not None
    assert msg.content == "Do you have black hoodies?"

    conv = added_objects[1]
    assert conv.window_expires_at > datetime.now(UTC) + timedelta(hours=23)
    assert mock_redis.publish.await_count == 1
