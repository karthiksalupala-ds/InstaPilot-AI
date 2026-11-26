import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

WorkspaceRole = Literal["owner", "admin", "operator", "viewer"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=120)
    workspace_name: str = Field(default="Private Workspace", min_length=2, max_length=120)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class WorkspaceSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: WorkspaceRole


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    workspaces: list[WorkspaceSummary]


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class MemberInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8)
    role: WorkspaceRole = "operator"


class MemberRoleUpdateRequest(BaseModel):
    role: WorkspaceRole


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
