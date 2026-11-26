import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import BaseTool, tool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge import KnowledgeDocument, Product
from app.models.messaging import Conversation, Customer, Message
from app.models.operations import Lead, Notification
from app.services.rag_service import search_knowledge_chunks

ALL_TOOL_NAMES = [
    "search_knowledge_base",
    "search_products",
    "get_product_details",
    "create_lead",
    "update_lead",
    "get_customer_history",
    "request_human_support",
    "send_instagram_reply",
]


@dataclass
class ToolContext:
    """Server-side execution context; never exposed as LLM arguments."""

    workspace_id: uuid.UUID
    instagram_account_id: uuid.UUID
    customer_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    automation_mode: str  # "auto" | "approval" | "manual"
    window_expires_at: datetime | None
    db: AsyncSession
    is_sandbox: bool = False
    send_callback: Callable[[str], Any] | None = None


def build_agent_tools(ctx: ToolContext, enabled_tools: list[str]) -> list[BaseTool]:
    """Create account-scoped LangChain tools filtered by the agent's allowlist."""

    @tool
    async def search_knowledge_base(query: str) -> str:
        """Search this Instagram account's FAQs, policies, and knowledge documents."""
        if get_settings().gemini_api_key:
            try:
                hits = await search_knowledge_chunks(
                    ctx.db, ctx.instagram_account_id, query, top_k=5
                )
                if hits:
                    return "\n\n".join(f"[{h['title']}] {h['content']}" for h in hits)
            except (ValueError, RuntimeError) as exc:
                logging.getLogger(__name__).warning("Semantic KB search fallback to SQL: %s", exc)

        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.instagram_account_id == ctx.instagram_account_id,
                KnowledgeDocument.is_enabled.is_(True),
                or_(
                    KnowledgeDocument.title.ilike(f"%{query}%"),
                    KnowledgeDocument.raw_content.ilike(f"%{query}%"),
                ),
            )
            .limit(5)
        )
        docs = (await ctx.db.scalars(stmt)).all()
        if not docs:
            return "NO_KNOWLEDGE_FOUND"
        return "\n\n".join(
            f"[{d.source_type.upper()}] {d.title}: {(d.raw_content or '')[:500]}" for d in docs
        )

    @tool
    async def search_products(query: str) -> str:
        """Search this Instagram account's product catalog for exact prices and stock."""
        stmt = (
            select(Product)
            .where(
                Product.instagram_account_id == ctx.instagram_account_id,
                Product.is_active.is_(True),
                or_(
                    Product.name.ilike(f"%{query}%"),
                    Product.description.ilike(f"%{query}%"),
                    Product.sku.ilike(f"%{query}%"),
                ),
            )
            .limit(5)
        )
        products = (await ctx.db.scalars(stmt)).all()
        if not products:
            return "NO_PRODUCTS_FOUND"
        lines = []
        for p in products:
            price = f"{p.currency} {p.price_cents / 100:.2f}"
            lines.append(
                f"ID={p.id} | SKU={p.sku or 'N/A'} | Name={p.name} | Price={price} | Stock={p.stock_status}"
            )
        return "\n".join(lines)

    @tool
    async def get_product_details(product_id_or_sku: str) -> str:
        """Get full details for a product by UUID or SKU."""
        stmt = select(Product).where(
            Product.instagram_account_id == ctx.instagram_account_id,
            Product.is_active.is_(True),
        )
        try:
            pid = uuid.UUID(product_id_or_sku)
            stmt = stmt.where(Product.id == pid)
        except ValueError:
            stmt = stmt.where(Product.sku == product_id_or_sku)

        product = await ctx.db.scalar(stmt)
        if product is None:
            return "PRODUCT_NOT_FOUND"
        price = f"{product.currency} {product.price_cents / 100:.2f}"
        return (
            f"Name: {product.name}\nSKU: {product.sku or 'N/A'}\nPrice: {price}\n"
            f"Stock: {product.stock_status}\nURL: {product.product_url or 'N/A'}\n"
            f"Description: {product.description or ''}"
        )

    @tool
    async def create_lead(
        interest_category: str,
        notes: str = "",
        estimated_value_cents: int | None = None,
    ) -> str:
        """Create a CRM lead for the current customer."""
        if ctx.is_sandbox or ctx.customer_id is None:
            return f"SANDBOX_LEAD_CREATED: {interest_category}"

        existing = await ctx.db.scalar(
            select(Lead).where(
                Lead.instagram_account_id == ctx.instagram_account_id,
                Lead.customer_id == ctx.customer_id,
                Lead.status.in_(["new", "qualified", "contacted"]),
            )
        )
        if existing is not None:
            return f"OPEN_LEAD_EXISTS: {existing.id} ({existing.status})"

        lead = Lead(
            workspace_id=ctx.workspace_id,
            instagram_account_id=ctx.instagram_account_id,
            customer_id=ctx.customer_id,
            conversation_id=ctx.conversation_id,
            status="new",
            interest_category=interest_category[:100],
            estimated_value_cents=estimated_value_cents,
            notes=notes,
        )
        ctx.db.add(lead)
        await ctx.db.flush()
        return f"LEAD_CREATED: {lead.id}"

    @tool
    async def update_lead(status: str, notes: str = "") -> str:
        """Update the customer's open CRM lead status (new, qualified, contacted, converted, lost)."""
        allowed = {"new", "qualified", "contacted", "converted", "lost"}
        if status not in allowed:
            return f"INVALID_STATUS: must be one of {sorted(allowed)}"
        if ctx.is_sandbox or ctx.customer_id is None:
            return f"SANDBOX_LEAD_UPDATED: {status}"

        lead = await ctx.db.scalar(
            select(Lead)
            .where(
                Lead.instagram_account_id == ctx.instagram_account_id,
                Lead.customer_id == ctx.customer_id,
            )
            .order_by(Lead.created_at.desc())
        )
        if lead is None:
            return "NO_LEAD_FOUND"
        lead.status = status
        if notes:
            lead.notes = f"{lead.notes or ''}\n{notes}".strip()
        await ctx.db.flush()
        return f"LEAD_UPDATED: {lead.id} -> {status}"

    @tool
    async def get_customer_history() -> str:
        """Retrieve past conversation summary and lead status for the current customer."""
        if ctx.is_sandbox or ctx.customer_id is None:
            return "SANDBOX_CUSTOMER: No prior history."

        customer = await ctx.db.scalar(
            select(Customer).where(
                Customer.id == ctx.customer_id,
                Customer.instagram_account_id == ctx.instagram_account_id,
            )
        )
        if customer is None:
            return "CUSTOMER_NOT_FOUND"
        lead = await ctx.db.scalar(
            select(Lead)
            .where(
                Lead.customer_id == ctx.customer_id,
                Lead.instagram_account_id == ctx.instagram_account_id,
            )
            .order_by(Lead.created_at.desc())
        )
        return (
            f"Username: @{customer.ig_username or 'unknown'} | Tags: {customer.tags} | "
            f"Notes: {customer.notes or 'None'} | "
            f"Latest Lead: {lead.status if lead else 'None'}"
        )

    @tool
    async def request_human_support(reason: str) -> str:
        """Escalate the conversation to a human operator and pause AI automation."""
        if ctx.is_sandbox:
            return f"SANDBOX_ESCALATED: {reason}"

        if ctx.conversation_id is not None:
            conv = await ctx.db.scalar(
                select(Conversation).where(
                    Conversation.id == ctx.conversation_id,
                    Conversation.instagram_account_id == ctx.instagram_account_id,
                )
            )
            if conv is not None:
                conv.status = "pending_human"
                conv.is_ai_paused = True

        ctx.db.add(
            Notification(
                workspace_id=ctx.workspace_id,
                instagram_account_id=ctx.instagram_account_id,
                type="escalation",
                title="Human Support Requested",
                body=reason[:500],
                link_url="/inbox",
            )
        )
        await ctx.db.flush()
        return "ESCALATED_TO_HUMAN"

    @tool
    async def send_instagram_reply(text: str) -> str:
        """Send a reply to the customer on Instagram (only permitted in Auto Mode within 24h window)."""
        if ctx.is_sandbox:
            return f"SANDBOX_WOULD_SEND: {text}"
        if ctx.automation_mode != "auto":
            return f"BLOCKED_BY_MODE: current mode is '{ctx.automation_mode}', not 'auto'"
        now = datetime.now(UTC)
        if ctx.window_expires_at is not None and ctx.window_expires_at <= now:
            return "BLOCKED_24H_WINDOW_EXPIRED"
        if ctx.send_callback is not None:
            await ctx.send_callback(text)
        if ctx.conversation_id is not None:
            ctx.db.add(
                Message(
                    workspace_id=ctx.workspace_id,
                    instagram_account_id=ctx.instagram_account_id,
                    conversation_id=ctx.conversation_id,
                    sender_type="ai_agent",
                    message_type="text",
                    content=text,
                    delivery_status="sent",
                    metadata_json={},
                )
            )
            await ctx.db.flush()
        return "SENT_TO_INSTAGRAM"

    registry: dict[str, BaseTool] = {
        "search_knowledge_base": search_knowledge_base,
        "search_products": search_products,
        "get_product_details": get_product_details,
        "create_lead": create_lead,
        "update_lead": update_lead,
        "get_customer_history": get_customer_history,
        "request_human_support": request_human_support,
        "send_instagram_reply": send_instagram_reply,
    }

    allowset = set(enabled_tools)
    return [t for name, t in registry.items() if name in allowset]
