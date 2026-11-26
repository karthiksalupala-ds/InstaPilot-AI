import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.main import app
from app.models.tenant import User, WorkspaceMember


def test_argon2id_password_hashing() -> None:
    hashed = hash_password("super-secret-pass")
    assert hashed != "super-secret-pass"
    assert verify_password("super-secret-pass", hashed) is True
    assert verify_password("wrong-pass", hashed) is False


def test_jwt_access_and_refresh_roundtrip() -> None:
    uid = str(uuid.uuid4())
    access = create_access_token(uid)
    refresh = create_refresh_token(uid)
    assert decode_token(access)["sub"] == uid
    assert decode_token(access)["type"] == "access"
    assert decode_token(refresh)["type"] == "refresh"


def test_bootstrap_blocked_when_users_exist() -> None:
    mock_db = AsyncMock()
    mock_db.scalar.return_value = 1

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/bootstrap",
            json={
                "email": "attacker@example.com",
                "password": "password123",
                "full_name": "Attacker",
            },
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_rbac_blocks_viewer_from_inviting_members() -> None:
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="viewer@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Viewer",
        is_active=True,
    )
    membership = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="viewer",
    )

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, membership])

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(workspace_id),
            },
            json={
                "email": "new@instapilot.local",
                "full_name": "New User",
                "password": "password123",
                "role": "operator",
            },
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_cross_workspace_isolation_returns_403() -> None:
    user_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="owner@instapilot.local",
        password_hash=hash_password("password123"),
        full_name="Owner",
        is_active=True,
    )

    mock_db = AsyncMock()
    # First scalar returns User, second scalar (membership lookup) returns None
    mock_db.scalar = AsyncMock(side_effect=[user, None])
    mock_db.execute = AsyncMock(return_value=MagicMock())

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.get(
            f"/api/v1/workspaces/{foreign_workspace_id}/members",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(foreign_workspace_id),
            },
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
