import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.core.crypto import decrypt_token
from app.db.session import get_db
from app.models.instagram import Agent, InstagramAccount, OAuthToken
from app.models.messaging import Conversation, Customer, Message
from app.models.tenant import WorkspaceMember
from app.schemas.inbox import (
    ApproveDraftRequest,
    ConversationDetailResponse,
    ConversationListItem,
    ConversationUpdateRequest,
    CustomerSummary,
    ManualReplyRequest,
    MessageResponse,
    RejectDraftRequest,
    SimulateCustomerDMRequest,
)
from app.services.agent_graph import run_agent_graph
from app.services.instagram_messaging import MetaAPIError, MetaInstagramMessagingClient

router = APIRouter(prefix="/inbox", tags=["inbox"])


def get_messaging_client() -> MetaInstagramMessagingClient:
    return MetaInstagramMessagingClient()


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    account_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationListItem]:
    """List conversations across all connected Instagram accounts in the workspace."""
    stmt = (
        select(Conversation, InstagramAccount.ig_username, Customer)
        .join(InstagramAccount, InstagramAccount.id == Conversation.instagram_account_id)
        .join(Customer, Customer.id == Conversation.customer_id)
        .where(Conversation.workspace_id == caller.workspace_id)
    )
    if account_id is not None:
        stmt = stmt.where(Conversation.instagram_account_id == account_id)
    if status_filter is not None:
        stmt = stmt.where(Conversation.status == status_filter)
    if unread_only:
        stmt = stmt.where(Conversation.unread_count > 0)

    stmt = stmt.order_by(Conversation.last_message_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        ConversationListItem(
            id=conv.id,
            instagram_account_id=conv.instagram_account_id,
            ig_username=ig_username,
            customer_username=cust.ig_username,
            customer_ig_id=cust.ig_scoped_user_id,
            channel=conv.channel,
            status=conv.status,
            is_ai_paused=conv.is_ai_paused,
            automation_mode_override=conv.automation_mode_override,
            last_intent=conv.last_intent,
            unread_count=conv.unread_count,
            window_expires_at=conv.window_expires_at,
            last_message_at=conv.last_message_at,
        )
        for conv, ig_username, cust in rows
    ]


@router.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conv_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Fetch a conversation thread, customer profile, and mark unread as read."""
    row = (
        await db.execute(
            select(Conversation, InstagramAccount.ig_username, Customer)
            .join(InstagramAccount, InstagramAccount.id == Conversation.instagram_account_id)
            .join(Customer, Customer.id == Conversation.customer_id)
            .where(Conversation.id == conv_id, Conversation.workspace_id == caller.workspace_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv, ig_username, cust = row
    if conv.unread_count > 0:
        conv.unread_count = 0
        await db.commit()

    msgs = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
    ).all()

    return ConversationDetailResponse(
        id=conv.id,
        instagram_account_id=conv.instagram_account_id,
        ig_username=ig_username,
        channel=conv.channel,
        status=conv.status,
        is_ai_paused=conv.is_ai_paused,
        automation_mode_override=conv.automation_mode_override,
        ai_summary=conv.ai_summary,
        last_intent=conv.last_intent,
        assigned_user_id=conv.assigned_user_id,
        window_expires_at=conv.window_expires_at,
        customer=CustomerSummary(
            id=cust.id,
            ig_scoped_user_id=cust.ig_scoped_user_id,
            ig_username=cust.ig_username,
            full_name=cust.full_name,
            tags=cust.tags,
            notes=cust.notes,
        ),
        messages=[
            MessageResponse(
                id=m.id,
                sender_type=m.sender_type,
                message_type=m.message_type,
                content=m.content,
                media_url=m.media_url,
                delivery_status=m.delivery_status,
                created_at=m.created_at,
            )
            for m in msgs
        ],
    )


async def _dispatch_to_instagram(
    *,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    conv_id: uuid.UUID,
    text: str,
    messaging_client: MetaInstagramMessagingClient,
) -> tuple[Conversation, InstagramAccount]:
    row = (
        await db.execute(
            select(Conversation, InstagramAccount, Customer, OAuthToken)
            .join(InstagramAccount, InstagramAccount.id == Conversation.instagram_account_id)
            .join(Customer, Customer.id == Conversation.customer_id)
            .join(OAuthToken, OAuthToken.instagram_account_id == InstagramAccount.id)
            .where(Conversation.id == conv_id, Conversation.workspace_id == workspace_id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation or OAuth token not found",
        )

    conv, account, cust, token_row = row
    now = datetime.now(UTC)
    if conv.window_expires_at is not None and conv.window_expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta 24-hour messaging window has expired for this conversation",
        )

    if cust.ig_scoped_user_id.startswith("sim_"):
        return conv, account

    access_token = decrypt_token(token_row.encrypted_access_token)
    try:
        await messaging_client.send_dm(
            ig_user_id=account.ig_user_id,
            recipient_igsid=cust.ig_scoped_user_id,
            text=text,
            access_token=access_token,
        )
    except (MetaAPIError, httpx.HTTPError) as exc:
        detail = str(exc) if isinstance(exc, MetaAPIError) else "Meta Send API request failed"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from exc

    return conv, account


@router.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
async def send_manual_reply(
    conv_id: uuid.UUID,
    payload: ManualReplyRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
    messaging_client: MetaInstagramMessagingClient = Depends(get_messaging_client),
) -> MessageResponse:
    """Send a manual human operator reply via Meta Send API."""
    conv, account = await _dispatch_to_instagram(
        db=db,
        workspace_id=caller.workspace_id,
        conv_id=conv_id,
        text=payload.text,
        messaging_client=messaging_client,
    )
    msg = Message(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        conversation_id=conv.id,
        sender_type="human_operator",
        message_type="text",
        content=payload.text,
        delivery_status="sent",
        metadata_json={"operator_id": str(caller.user_id)},
    )
    db.add(msg)
    conv.last_message_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(msg)
    return MessageResponse(
        id=msg.id,
        sender_type=msg.sender_type,
        message_type=msg.message_type,
        content=msg.content,
        media_url=msg.media_url,
        delivery_status=msg.delivery_status,
        created_at=msg.created_at,
    )


@router.post("/conversations/{conv_id}/approve-draft", response_model=MessageResponse)
async def approve_ai_draft(
    conv_id: uuid.UUID,
    payload: ApproveDraftRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
    messaging_client: MetaInstagramMessagingClient = Depends(get_messaging_client),
) -> MessageResponse:
    """Approve (and optionally edit) a pending AI draft and send via Meta Send API."""
    draft = await db.scalar(
        select(Message).where(
            Message.id == payload.message_id,
            Message.conversation_id == conv_id,
            Message.workspace_id == caller.workspace_id,
            Message.delivery_status == "pending_approval",
        )
    )
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending draft not found")

    final_text = payload.edited_text or draft.content
    conv, _account = await _dispatch_to_instagram(
        db=db,
        workspace_id=caller.workspace_id,
        conv_id=conv_id,
        text=final_text,
        messaging_client=messaging_client,
    )
    draft.content = final_text
    draft.delivery_status = "sent"
    conv.last_message_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(draft)
    return MessageResponse(
        id=draft.id,
        sender_type=draft.sender_type,
        message_type=draft.message_type,
        content=draft.content,
        media_url=draft.media_url,
        delivery_status=draft.delivery_status,
        created_at=draft.created_at,
    )


@router.post("/conversations/{conv_id}/reject-draft", response_model=MessageResponse)
async def reject_ai_draft(
    conv_id: uuid.UUID,
    payload: RejectDraftRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reject a pending AI draft without sending it."""
    draft = await db.scalar(
        select(Message).where(
            Message.id == payload.message_id,
            Message.conversation_id == conv_id,
            Message.workspace_id == caller.workspace_id,
            Message.delivery_status == "pending_approval",
        )
    )
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending draft not found")

    draft.delivery_status = "rejected"
    await db.commit()
    await db.refresh(draft)
    return MessageResponse(
        id=draft.id,
        sender_type=draft.sender_type,
        message_type=draft.message_type,
        content=draft.content,
        media_url=draft.media_url,
        delivery_status=draft.delivery_status,
        created_at=draft.created_at,
    )


@router.patch("/conversations/{conv_id}")
async def update_conversation(
    conv_id: uuid.UUID,
    payload: ConversationUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Update conversation status, human assignee, or AI pause/mode override."""
    conv = await db.scalar(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.workspace_id == caller.workspace_id,
        )
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(conv, k, v)
    await db.commit()
    return {
        "id": str(conv.id),
        "status": conv.status,
        "is_ai_paused": conv.is_ai_paused,
        "automation_mode_override": conv.automation_mode_override,
        "assigned_user_id": str(conv.assigned_user_id) if conv.assigned_user_id else None,
    }


@router.post("/simulate")
async def simulate_customer_dm(
    payload: SimulateCustomerDMRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Simulate an incoming customer DM and run the live LangGraph agent into Unified Inbox."""
    row = (
        await db.execute(
            select(InstagramAccount, Agent)
            .join(Agent, Agent.instagram_account_id == InstagramAccount.id)
            .where(
                InstagramAccount.id == payload.instagram_account_id,
                InstagramAccount.workspace_id == caller.workspace_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account or agent not found")

    account, agent = row
    now = datetime.now(UTC)
    igsid = f"sim_{payload.customer_username.lstrip('@').lower()}"

    customer = await db.scalar(
        select(Customer).where(
            Customer.instagram_account_id == account.id,
            Customer.ig_scoped_user_id == igsid,
        )
    )
    if customer is None:
        customer = Customer(
            workspace_id=caller.workspace_id,
            instagram_account_id=account.id,
            ig_scoped_user_id=igsid,
            ig_username=payload.customer_username.lstrip("@"),
        )
        db.add(customer)
        await db.flush()

    conv = await db.scalar(
        select(Conversation).where(
            Conversation.instagram_account_id == account.id,
            Conversation.customer_id == customer.id,
            Conversation.channel == "dm",
        )
    )
    if conv is None:
        conv = Conversation(
            workspace_id=caller.workspace_id,
            instagram_account_id=account.id,
            customer_id=customer.id,
            channel="dm",
            status="open",
            window_expires_at=now + timedelta(hours=24),
            unread_count=1,
            last_message_at=now,
        )
        db.add(conv)
        await db.flush()
    else:
        conv.window_expires_at = now + timedelta(hours=24)
        conv.last_message_at = now

    msg = Message(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        conversation_id=conv.id,
        sender_type="customer",
        message_type="text",
        content=payload.message,
        delivery_status="received",
        metadata_json={"simulated": True},
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    agent_result = await run_agent_graph(
        db=db,
        account=account,
        agent=agent,
        customer_message=msg.content,
        conversation=conv,
        trigger_message=msg,
        is_sandbox=False,
    )
    return {
        "conversation_id": str(conv.id),
        "agent_result": agent_result,
    }
