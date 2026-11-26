import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.db.session import get_db
from app.models.messaging import Message
from app.models.operations import AgentExecutionLog, Lead, Notification
from app.models.tenant import WorkspaceMember
from app.schemas.analytics import (
    AgentExecutionLogResponse,
    AnalyticsOverviewResponse,
    NotificationResponse,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    account_id: uuid.UUID | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Aggregate workspace (or account) KPIs over the requested lookback window."""
    since = datetime.now(UTC) - timedelta(days=days)

    msg_filter = [Message.workspace_id == caller.workspace_id, Message.created_at >= since]
    log_filter = [
        AgentExecutionLog.workspace_id == caller.workspace_id,
        AgentExecutionLog.created_at >= since,
    ]
    lead_filter = [Lead.workspace_id == caller.workspace_id, Lead.created_at >= since]

    if account_id is not None:
        msg_filter.append(Message.instagram_account_id == account_id)
        log_filter.append(AgentExecutionLog.instagram_account_id == account_id)
        lead_filter.append(Lead.instagram_account_id == account_id)

    total_messages = int(await db.scalar(select(func.count()).select_from(Message).where(*msg_filter)) or 0)
    ai_sent_count = int(
        await db.scalar(
            select(func.count())
            .select_from(AgentExecutionLog)
            .where(*log_filter, AgentExecutionLog.final_action == "sent")
        )
        or 0
    )
    pending_approvals = int(
        await db.scalar(
            select(func.count())
            .select_from(Message)
            .where(*msg_filter, Message.delivery_status == "pending_approval")
        )
        or 0
    )
    escalated_count = int(
        await db.scalar(
            select(func.count())
            .select_from(AgentExecutionLog)
            .where(*log_filter, AgentExecutionLog.final_action == "escalated")
        )
        or 0
    )
    avg_latency = float(
        await db.scalar(select(func.avg(AgentExecutionLog.latency_ms)).where(*log_filter)) or 0.0
    )
    total_tokens = int(
        await db.scalar(
            select(
                func.coalesce(
                    func.sum(AgentExecutionLog.tokens_prompt + AgentExecutionLog.tokens_completion), 0
                )
            ).where(*log_filter)
        )
        or 0
    )
    total_leads = int(await db.scalar(select(func.count()).select_from(Lead).where(*lead_filter)) or 0)
    converted_leads = int(
        await db.scalar(
            select(func.count()).select_from(Lead).where(*lead_filter, Lead.status == "converted")
        )
        or 0
    )

    return AnalyticsOverviewResponse(
        total_messages=total_messages,
        ai_sent_count=ai_sent_count,
        pending_approvals=pending_approvals,
        escalated_count=escalated_count,
        avg_latency_ms=round(avg_latency, 1),
        total_leads=total_leads,
        converted_leads=converted_leads,
        total_tokens=total_tokens,
    )


@router.get("/logs/agent-executions", response_model=list[AgentExecutionLogResponse])
async def list_agent_execution_logs(
    account_id: uuid.UUID | None = Query(default=None),
    final_action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[AgentExecutionLogResponse]:
    """List paginated LangGraph execution audit logs for the workspace."""
    stmt = select(AgentExecutionLog).where(AgentExecutionLog.workspace_id == caller.workspace_id)
    if account_id is not None:
        stmt = stmt.where(AgentExecutionLog.instagram_account_id == account_id)
    if final_action is not None:
        stmt = stmt.where(AgentExecutionLog.final_action == final_action)

    rows = (await db.scalars(stmt.order_by(AgentExecutionLog.created_at.desc()).limit(limit))).all()
    return [
        AgentExecutionLogResponse(
            id=r.id,
            instagram_account_id=r.instagram_account_id,
            conversation_id=r.conversation_id,
            intent=r.intent,
            tools_called=r.tools_called,
            draft_response=r.draft_response,
            final_action=r.final_action,
            llm_provider=r.llm_provider,
            llm_model=r.llm_model,
            tokens_prompt=r.tokens_prompt,
            tokens_completion=r.tokens_completion,
            latency_ms=r.latency_ms,
            error_message=r.error_message,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    """List workspace notifications (escalations, approvals, token expiry, errors)."""
    stmt = select(Notification).where(
        Notification.workspace_id == caller.workspace_id,
        or_(Notification.user_id.is_(None), Notification.user_id == caller.user_id),
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    rows = (await db.scalars(stmt.order_by(Notification.created_at.desc()).limit(limit))).all()
    return [
        NotificationResponse(
            id=n.id,
            instagram_account_id=n.instagram_account_id,
            type=n.type,
            title=n.title,
            body=n.body,
            link_url=n.link_url,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in rows
    ]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a single notification as read."""
    notif = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == caller.workspace_id,
        )
    )
    if notif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    await db.commit()
    return NotificationResponse(
        id=notif.id,
        instagram_account_id=notif.instagram_account_id,
        type=notif.type,
        title=notif.title,
        body=notif.body,
        link_url=notif.link_url,
        is_read=notif.is_read,
        created_at=notif.created_at,
    )


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all unread workspace notifications as read."""
    await db.execute(
        update(Notification)
        .where(
            Notification.workspace_id == caller.workspace_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
