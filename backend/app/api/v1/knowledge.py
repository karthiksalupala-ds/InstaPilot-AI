import uuid
from collections.abc import AsyncGenerator

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models.instagram import InstagramAccount
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, Product
from app.models.tenant import WorkspaceMember
from app.schemas.knowledge import (
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.services.rag_service import (
    extract_pdf_text,
    search_knowledge_chunks,
    validate_public_url,
)

router = APIRouter(prefix="/accounts/{account_id}", tags=["knowledge"])


async def get_arq_pool() -> AsyncGenerator[ArqRedis, None]:
    pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    try:
        yield pool
    finally:
        await pool.aclose()


async def _get_account_and_kb(
    account_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[InstagramAccount, KnowledgeBase]:
    account = await db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.id == account_id,
            InstagramAccount.workspace_id == workspace_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    kb = await db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.instagram_account_id == account.id)
    )
    if kb is None:
        kb = KnowledgeBase(
            workspace_id=workspace_id,
            instagram_account_id=account.id,
            name=f"@{account.ig_username} Knowledge Base",
        )
        db.add(kb)
        await db.flush()
    return account, kb


@router.get("/knowledge/documents", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    """List knowledge documents for an Instagram account."""
    account, _kb = await _get_account_and_kb(account_id, caller.workspace_id, db)
    docs = (
        await db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.instagram_account_id == account.id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
    ).all()
    return [
        KnowledgeDocumentResponse(
            id=d.id,
            instagram_account_id=d.instagram_account_id,
            source_type=d.source_type,
            title=d.title,
            source_url=d.source_url,
            status=d.status,
            is_enabled=d.is_enabled,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.post(
    "/knowledge/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    account_id: uuid.UUID,
    payload: KnowledgeDocumentCreateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> KnowledgeDocumentResponse:
    """Create a manual text, FAQ, policy, or website URL knowledge document."""
    account, kb = await _get_account_and_kb(account_id, caller.workspace_id, db)

    if payload.source_type == "website_url":
        if not payload.source_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="source_url is required"
            )
        try:
            validate_public_url(payload.source_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    elif not payload.raw_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="raw_content is required"
        )

    doc = KnowledgeDocument(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        knowledge_base_id=kb.id,
        source_type=payload.source_type,
        title=payload.title,
        raw_content=payload.raw_content,
        source_url=payload.source_url,
        status="pending",
        is_enabled=payload.is_enabled,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await arq_pool.enqueue_job("index_knowledge_document_job", str(doc.id))
    return KnowledgeDocumentResponse(
        id=doc.id,
        instagram_account_id=doc.instagram_account_id,
        source_type=doc.source_type,
        title=doc.title,
        source_url=doc.source_url,
        status=doc.status,
        is_enabled=doc.is_enabled,
        created_at=doc.created_at,
    )


@router.post(
    "/knowledge/upload-pdf",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf_document(
    account_id: uuid.UUID,
    title: str = Form(..., min_length=2, max_length=200),
    file: UploadFile = File(...),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> KnowledgeDocumentResponse:
    """Upload a PDF document (<= 10 MB), extract text safely, and enqueue RAG indexing."""
    account, kb = await _get_account_and_kb(account_id, caller.workspace_id, db)
    pdf_bytes = await file.read()
    try:
        extracted_text = extract_pdf_text(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    doc = KnowledgeDocument(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        knowledge_base_id=kb.id,
        source_type="pdf",
        title=title,
        raw_content=extracted_text,
        file_path=file.filename,
        status="pending",
        is_enabled=True,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await arq_pool.enqueue_job("index_knowledge_document_job", str(doc.id))
    return KnowledgeDocumentResponse(
        id=doc.id,
        instagram_account_id=doc.instagram_account_id,
        source_type=doc.source_type,
        title=doc.title,
        source_url=doc.source_url,
        status=doc.status,
        is_enabled=doc.is_enabled,
        created_at=doc.created_at,
    )


@router.delete("/knowledge/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    account_id: uuid.UUID,
    doc_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a knowledge document and cascade-delete its vector chunks."""
    doc = await db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.instagram_account_id == account_id,
            KnowledgeDocument.workspace_id == caller.workspace_id,
        )
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.delete(doc)
    await db.commit()


@router.post("/knowledge/search", response_model=list[KnowledgeSearchHit])
async def search_knowledge(
    account_id: uuid.UUID,
    payload: KnowledgeSearchRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeSearchHit]:
    """Test semantic pgvector retrieval for an Instagram account."""
    account, _kb = await _get_account_and_kb(account_id, caller.workspace_id, db)
    hits = await search_knowledge_chunks(db, account.id, payload.query, top_k=payload.top_k)
    return [KnowledgeSearchHit(**h) for h in hits]


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    """List products in this Instagram account's catalog."""
    account, _kb = await _get_account_and_kb(account_id, caller.workspace_id, db)
    items = (
        await db.scalars(
            select(Product).where(Product.instagram_account_id == account.id)
        )
    ).all()
    return [
        ProductResponse(
            id=p.id,
            instagram_account_id=p.instagram_account_id,
            sku=p.sku,
            name=p.name,
            description=p.description,
            price_cents=p.price_cents,
            currency=p.currency,
            stock_status=p.stock_status,
            product_url=p.product_url,
            is_active=p.is_active,
        )
        for p in items
    ]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    account_id: uuid.UUID,
    payload: ProductCreateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Add a structured product to this Instagram account's catalog."""
    account, _kb = await _get_account_and_kb(account_id, caller.workspace_id, db)
    product = Product(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        price_cents=payload.price_cents,
        currency=payload.currency,
        stock_status=payload.stock_status,
        product_url=payload.product_url,
        metadata_json=payload.metadata_json,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse(
        id=product.id,
        instagram_account_id=product.instagram_account_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        price_cents=product.price_cents,
        currency=product.currency,
        stock_status=product.stock_status,
        product_url=product.product_url,
        is_active=product.is_active,
    )


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    account_id: uuid.UUID,
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product in this Instagram account's catalog."""
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.instagram_account_id == account_id,
            Product.workspace_id == caller.workspace_id,
        )
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    await db.commit()
    await db.refresh(product)
    return ProductResponse(
        id=product.id,
        instagram_account_id=product.instagram_account_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        price_cents=product.price_cents,
        currency=product.currency,
        stock_status=product.stock_status,
        product_url=product.product_url,
        is_active=product.is_active,
    )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    account_id: uuid.UUID,
    product_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a product from this Instagram account's catalog."""
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.instagram_account_id == account_id,
            Product.workspace_id == caller.workspace_id,
        )
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    await db.delete(product)
    await db.commit()
