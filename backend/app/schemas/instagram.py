import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

AutomationMode = Literal["auto", "approval", "manual"]


class OAuthAuthorizeResponse(BaseModel):
    authorize_url: str


class InstagramAccountResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    ig_user_id: str
    ig_username: str
    account_type: str
    profile_picture_url: str | None
    connection_status: str
    automation_mode: str
    is_agent_enabled: bool
    webhook_subscribed: bool
    last_webhook_at: datetime | None
    token_expires_at: datetime | None = None


class InstagramAccountUpdateRequest(BaseModel):
    is_agent_enabled: bool | None = None
    automation_mode: AutomationMode | None = None
