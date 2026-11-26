import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.db.session import get_db
from app.models.instagram import InstagramAccount
from app.models.messaging import Customer
from app.models.operations import Lead
from app.models.tenant import WorkspaceMember
from app.schemas.crm import LeadCreateRequest, LeadResponse, LeadUpdateRequest

router = APIRouter(prefix="/leads", tags=["leads"])


def _to_response(lead: Lead) -> LeadResponse:
    return LeadResponse(
        id=lead.id,
        workspace_id=lead.workspace_id,
        instagram_account_id=lead.instagram_account_id,
        customer_id=lead.customer_id,
        conversation_id=lead.conversation_id,
        status=lead.status,
        interest_category=lead.interest_category,
        estimated_value_cents=lead.estimated_value_cents,
        notes=lead.notes,
        follow_up_at=lead.follow_up_at,
        assigned_user_id=lead.assigned_user_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    account_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    due_only: bool = Query(default=False),
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[LeadResponse]:
    """List CRM leads in the active workspace with optional account/status/reminder filters."""
    stmt = select(Lead).where(Lead.workspace_id == caller.workspace_id)
    if account_id is not None:
        stmt = stmt.where(Lead.instagram_account_id == account_id)
    if status_filter is not None:
        stmt = stmt.where(Lead.status == status_filter)
    if due_only:
        stmt = stmt.where(Lead.follow_up_at.is_not(None), Lead.follow_up_at <= datetime.now(UTC))

    leads = (await db.scalars(stmt.order_by(Lead.updated_at.desc()))).all()
    return [_to_response(lead) for lead in leads]


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Create a CRM lead for an account-scoped customer."""
    account = await db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.id == payload.instagram_account_id,
            InstagramAccount.workspace_id == caller.workspace_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    customer = await db.scalar(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.instagram_account_id == account.id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    lead = Lead(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        customer_id=customer.id,
        conversation_id=payload.conversation_id,
        status=payload.status,
        interest_category=payload.interest_category,
        estimated_value_cents=payload.estimated_value_cents,
        notes=payload.notes,
        follow_up_at=payload.follow_up_at,
        assigned_user_id=payload.assigned_user_id,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return _to_response(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Update lead status, notes, follow-up reminder, or assignee."""
    lead = await db.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.workspace_id == caller.workspace_id)
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lead, k, v)
    await db.commit()
    await db.refresh(lead)
    return _to_response(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a lead."""
    lead = await db.scalar(
        select(Lead).where(Lead.id == lead_id, Lead.workspace_id == caller.workspace_id)
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
