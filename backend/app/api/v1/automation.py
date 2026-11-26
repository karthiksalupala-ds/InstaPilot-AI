import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.db.session import get_db
from app.models.instagram import InstagramAccount
from app.models.operations import AutomationRule
from app.models.tenant import WorkspaceMember
from app.schemas.crm import (
    AutomationRuleCreateRequest,
    AutomationRuleResponse,
    AutomationRuleUpdateRequest,
)

router = APIRouter(prefix="/accounts/{account_id}/automation-rules", tags=["automation"])


def _to_response(rule: AutomationRule) -> AutomationRuleResponse:
    return AutomationRuleResponse(
        id=rule.id,
        instagram_account_id=rule.instagram_account_id,
        name=rule.name,
        trigger_type=rule.trigger_type,
        conditions=rule.conditions,
        actions=rule.actions,
        priority=rule.priority,
        is_enabled=rule.is_enabled,
        created_at=rule.created_at,
    )


@router.get("", response_model=list[AutomationRuleResponse])
async def list_rules(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[AutomationRuleResponse]:
    """List automation rules for an Instagram account."""
    rules = (
        await db.scalars(
            select(AutomationRule)
            .where(
                AutomationRule.instagram_account_id == account_id,
                AutomationRule.workspace_id == caller.workspace_id,
            )
            .order_by(AutomationRule.priority.asc())
        )
    ).all()
    return [_to_response(r) for r in rules]


@router.post("", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    account_id: uuid.UUID,
    payload: AutomationRuleCreateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> AutomationRuleResponse:
    """Create an automation rule for an Instagram account."""
    account = await db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.id == account_id,
            InstagramAccount.workspace_id == caller.workspace_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    rule = AutomationRule(
        workspace_id=caller.workspace_id,
        instagram_account_id=account.id,
        name=payload.name,
        trigger_type=payload.trigger_type,
        conditions=payload.conditions,
        actions=payload.actions,
        priority=payload.priority,
        is_enabled=payload.is_enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _to_response(rule)


@router.patch("/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(
    account_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AutomationRuleUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> AutomationRuleResponse:
    """Update an automation rule."""
    rule = await db.scalar(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.instagram_account_id == account_id,
            AutomationRule.workspace_id == caller.workspace_id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return _to_response(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    account_id: uuid.UUID,
    rule_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an automation rule."""
    rule = await db.scalar(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.instagram_account_id == account_id,
            AutomationRule.workspace_id == caller.workspace_id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
