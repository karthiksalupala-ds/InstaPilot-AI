import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_workspace_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.tenant import User, Workspace, WorkspaceMember
from app.schemas.auth import (
    MemberInviteRequest,
    MemberResponse,
    MemberRoleUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceSummary,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    return f"{base}-{uuid.uuid4().hex[:6]}"


@router.get("", response_model=list[WorkspaceSummary])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceSummary]:
    """List workspaces the current user belongs to."""
    rows = (
        await db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == current_user.id)
        )
    ).all()
    return [
        WorkspaceSummary(id=ws.id, name=ws.name, slug=ws.slug, role=role)  # type: ignore[arg-type]
        for ws, role in rows
    ]


@router.post("", response_model=WorkspaceSummary, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSummary:
    """Create a new workspace owned by the current user."""
    workspace = Workspace(
        name=payload.name,
        slug=_slugify(payload.name),
        owner_id=current_user.id,
        plan_tier="private",
    )
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role="owner"))
    await db.commit()
    return WorkspaceSummary(
        id=workspace.id, name=workspace.name, slug=workspace.slug, role="owner"
    )


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_members(
    workspace_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    """List members of the active workspace."""
    if caller.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace mismatch")

    rows = (
        await db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    return [
        MemberResponse(
            id=m.id, user_id=u.id, email=u.email, full_name=u.full_name, role=m.role
        )
        for m, u in rows
    ]


@router.post("/{workspace_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: uuid.UUID,
    payload: MemberInviteRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Invite/add a user to the workspace (owner/admin only)."""
    if caller.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace mismatch")

    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        user = User(
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
        )
        db.add(user)
        await db.flush()

    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member")

    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=payload.role)
    db.add(member)
    await db.commit()
    return MemberResponse(
        id=member.id, user_id=user.id, email=user.email, full_name=user.full_name, role=member.role
    )


@router.patch("/{workspace_id}/members/{member_id}", response_model=MemberResponse)
async def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberRoleUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Update a workspace member's role (owner/admin only)."""
    if caller.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace mismatch")

    row = (
        await db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member, user = row
    member.role = payload.role
    await db.commit()
    return MemberResponse(
        id=member.id, user_id=user.id, email=user.email, full_name=user.full_name, role=member.role
    )
