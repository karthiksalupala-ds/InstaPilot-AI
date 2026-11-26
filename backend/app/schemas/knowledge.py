import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["manual_text", "faq", "policy", "website_url"]
StockStatus = Literal["in_stock", "out_of_stock", "preorder"]


class KnowledgeDocumentCreateRequest(BaseModel):
    source_type: SourceType
    title: str = Field(min_length=2, max_length=200)
    raw_content: str | None = None
    source_url: str | None = None
    is_enabled: bool = True


class KnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    source_type: str
    title: str
    source_url: str | None
    status: str
    is_enabled: bool
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class KnowledgeSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float


class ProductCreateRequest(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    price_cents: int = Field(ge=0)
    currency: str = Field(default="INR", max_length=8)
    stock_status: StockStatus = "in_stock"
    product_url: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ProductUpdateRequest(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    stock_status: StockStatus | None = None
    product_url: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    sku: str | None
    name: str
    description: str | None
    price_cents: int
    currency: str
    stock_status: str
    product_url: str | None
    is_active: bool
