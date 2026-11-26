import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.db.session import get_db
from app.models.instagram import Agent, InstagramAccount
from app.models.tenant import WorkspaceMember
from app.schemas.agent import AgentResponse, AgentUpdateRequest, SandboxRequest, SandboxResponse
from app.services.agent_graph import run_agent_graph
from app.services.agent_tools import ALL_TOOL_NAMES

router = APIRouter(prefix="/accounts/{account_id}/agent", tags=["agents"])


async def _get_account_and_agent(
    account_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[InstagramAccount, Agent]:
    row = (
        await db.execute(
            select(InstagramAccount, Agent)
            .join(Agent, Agent.instagram_account_id == InstagramAccount.id)
            .where(
                InstagramAccount.id == account_id,
                InstagramAccount.workspace_id == workspace_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return row[0], row[1]


@router.get("", response_model=AgentResponse)
async def get_agent_config(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Fetch the AI agent configuration for a connected Instagram account."""
    _account, agent = await _get_account_and_agent(account_id, caller.workspace_id, db)
    return AgentResponse(
        id=agent.id,
        instagram_account_id=agent.instagram_account_id,
        name=agent.name,
        system_instructions=agent.system_instructions,
        personality=agent.personality,
        communication_style=agent.communication_style,
        language_config=agent.language_config,
        llm_provider=agent.llm_provider,
        llm_model=agent.llm_model,
        temperature=agent.temperature,
        enabled_tools=agent.enabled_tools,
        escalation_config=agent.escalation_config,
    )


@router.patch("", response_model=AgentResponse)
async def update_agent_config(
    account_id: uuid.UUID,
    payload: AgentUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Update an Instagram account's AI agent settings."""
    _account, agent = await _get_account_and_agent(account_id, caller.workspace_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "enabled_tools" in data:
        invalid = set(data["enabled_tools"]) - set(ALL_TOOL_NAMES)
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tool names: {sorted(invalid)}",
            )
    for key, value in data.items():
        setattr(agent, key, value)
    await db.commit()
    return AgentResponse(
        id=agent.id,
        instagram_account_id=agent.instagram_account_id,
        name=agent.name,
        system_instructions=agent.system_instructions,
        personality=agent.personality,
        communication_style=agent.communication_style,
        language_config=agent.language_config,
        llm_provider=agent.llm_provider,
        llm_model=agent.llm_model,
        temperature=agent.temperature,
        enabled_tools=agent.enabled_tools,
        escalation_config=agent.escalation_config,
    )


@router.post("/sandbox", response_model=SandboxResponse)
async def run_agent_sandbox(
    account_id: uuid.UUID,
    payload: SandboxRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
) -> SandboxResponse:
    """Run a dry-run simulation against the agent without sending to Instagram."""
    account, agent = await _get_account_and_agent(account_id, caller.workspace_id, db)
    result = await run_agent_graph(
        db=db,
        account=account,
        agent=agent,
        customer_message=payload.message,
        is_sandbox=True,
    )
    return SandboxResponse(**result)
