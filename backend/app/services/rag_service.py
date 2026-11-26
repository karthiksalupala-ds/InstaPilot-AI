import ipaddress
import socket
import uuid
from collections.abc import Awaitable, Callable
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB

EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks without losing boundary context."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    step = max(chunk_size - overlap, 100)
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start += step
    return chunks


def validate_public_url(url: str) -> str:
    """Validate that a URL uses HTTP(S) and does not resolve to private/loopback IPs (SSRF guard)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http:// or https:// with a valid hostname")

    hostname = parsed.hostname
    if hostname.lower() in {"localhost", "metadata.google.internal"}:
        raise ValueError("Access to local or metadata hostnames is forbidden")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname: {hostname}") from exc

    for info in addr_info:
        ip_str = str(info[4][0])
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
        ):
            raise ValueError(f"Blocked non-public IP address: {ip_str}")

    return url.strip()


async def fetch_url_text(url: str) -> str:
    """Safely fetch a permitted public URL and extract visible text."""
    safe_url = validate_public_url(url)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        resp = await client.get(safe_url, headers={"User-Agent": "InstaPilotBot/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Validate magic bytes and size, then extract text from a PDF safely."""
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds 10 MB limit")
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Invalid PDF file signature")

    reader = PdfReader(BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if not text:
        raise ValueError("No extractable text found in PDF")
    return text


async def default_embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate 768-dim embeddings using Google Gemini Embeddings."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for generating embeddings")
    embedder = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        api_key=settings.gemini_api_key,  # type: ignore[arg-type]
        output_dimensionality=768,
    )
    return await embedder.aembed_documents(texts)


async def index_knowledge_document(
    db: AsyncSession,
    doc: KnowledgeDocument,
    embed_fn: EmbedFn | None = None,
) -> int:
    """Chunk, embed, and store KnowledgeChunks for a single account-isolated document."""
    try:
        raw = doc.raw_content or ""
        if doc.source_type == "website_url" and not raw and doc.source_url:
            raw = await fetch_url_text(doc.source_url)
            doc.raw_content = raw

        chunks = chunk_text(raw)
        if not chunks:
            doc.status = "failed"
            await db.commit()
            return 0

        fn = embed_fn or default_embed_texts
        vectors = await fn(chunks)

        await db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
        )

        for idx, (chunk_str, vec) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                KnowledgeChunk(
                    id=uuid.uuid4(),
                    workspace_id=doc.workspace_id,
                    instagram_account_id=doc.instagram_account_id,
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_str,
                    metadata_json={"title": doc.title, "source_type": doc.source_type},
                    embedding=vec,
                )
            )
        doc.status = "indexed"
        await db.commit()
        return len(chunks)
    except Exception:
        doc.status = "failed"
        await db.commit()
        raise


async def search_knowledge_chunks(
    db: AsyncSession,
    instagram_account_id: uuid.UUID,
    query: str,
    top_k: int = 5,
    embed_fn: EmbedFn | None = None,
) -> list[dict[str, Any]]:
    """Semantic pgvector cosine search strictly isolated to a single Instagram account."""
    fn = embed_fn or default_embed_texts
    query_vec = (await fn([query]))[0]
    distance_expr = KnowledgeChunk.embedding.cosine_distance(query_vec)

    stmt = (
        select(KnowledgeChunk, KnowledgeDocument.title, distance_expr.label("distance"))
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(
            KnowledgeChunk.instagram_account_id == instagram_account_id,
            KnowledgeDocument.is_enabled.is_(True),
        )
        .order_by(distance_expr.asc())
        .limit(min(top_k, 10))
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "title": title,
            "content": chunk.content,
            "score": max(0.0, 1.0 - float(dist)),
        }
        for chunk, title, dist in rows
    ]
