import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.knowledge import get_arq_pool
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.instagram import InstagramAccount
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.models.tenant import User, WorkspaceMember
from app.services.rag_service import (
    chunk_text,
    extract_pdf_text,
    index_knowledge_document,
    validate_public_url,
)


def test_chunk_text_with_overlap() -> None:
    text = "word " * 400  # 2000 chars
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) >= 2
    assert all(len(c) <= 1000 for c in chunks)


def test_ssrf_guard_blocks_private_and_local_urls() -> None:
    for bad_url in [
        "http://127.0.0.1/admin",
        "http://localhost:8000/secret",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://example.com/file",
    ]:
        with pytest.raises(ValueError):
            validate_public_url(bad_url)


def test_pdf_extractor_rejects_invalid_magic_bytes() -> None:
    with pytest.raises(ValueError, match="Invalid PDF"):
        extract_pdf_text(b"not a real pdf file")


async def test_index_knowledge_document_creates_chunks() -> None:
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    doc = KnowledgeDocument(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        knowledge_base_id=uuid.uuid4(),
        source_type="policy",
        title="Shipping Policy",
        raw_content="Free shipping across India on orders above INR 999. Delivery takes 3-5 days.",
        status="pending",
        is_enabled=True,
    )

    added: list[object] = []
    mock_db = AsyncMock()
    mock_db.add = lambda obj: added.append(obj)

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    count = await index_knowledge_document(mock_db, doc, embed_fn=fake_embed)
    assert count == 1
    assert doc.status == "indexed"
    assert len(added) == 1
    assert isinstance(added[0], KnowledgeChunk)
    assert added[0].instagram_account_id == acc_id


def test_knowledge_url_ssrf_blocked_at_api_boundary() -> None:
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
        id=uuid.uuid4(), workspace_id=workspace_id, user_id=user_id, role="owner"
    )
    account = InstagramAccount(
        id=account_id,
        workspace_id=workspace_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
    )
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        instagram_account_id=account_id,
        name="KB",
    )

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(side_effect=[user, member, account, kb])

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_arq_pool] = lambda: AsyncMock()
    try:
        token = create_access_token(str(user_id))
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/accounts/{account_id}/knowledge/documents",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-Id": str(workspace_id),
            },
            json={
                "source_type": "website_url",
                "title": "Internal Metadata",
                "source_url": "http://169.254.169.254/latest/meta-data/",
            },
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
