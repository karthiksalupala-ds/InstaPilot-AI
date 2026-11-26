import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ConversationStatus = Literal["open", "pending_human", "resolved", "snoozed"]
AutomationOverride = Literal["auto", "approval", "manual"]


class CustomerSummary(BaseModel):
    id: uuid.UUID
    ig_scoped_user_id: str
    ig_username: str | None
    full_name: str | None
    tags: list[str]
    notes: str | None


class MessageResponse(BaseModel):
    id: uuid.UUID
    sender_type: str
    message_type: str
    content: str
    media_url: str | None
    delivery_status: str
    created_at: datetime


class ConversationListItem(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    ig_username: str
    customer_username: str | None
    customer_ig_id: str
    channel: str
    status: str
    is_ai_paused: bool
    automation_mode_override: str | None
    last_intent: str | None
    unread_count: int
    window_expires_at: datetime | None
    last_message_at: datetime


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    ig_username: str
    channel: str
    status: str
    is_ai_paused: bool
    automation_mode_override: str | None
    ai_summary: str | None
    last_intent: str | None
    assigned_user_id: uuid.UUID | None
    window_expires_at: datetime | None
    customer: CustomerSummary
    messages: list[MessageResponse]


class ManualReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ApproveDraftRequest(BaseModel):
    message_id: uuid.UUID
    edited_text: str | None = Field(default=None, min_length=1, max_length=1000)


class RejectDraftRequest(BaseModel):
    message_id: uuid.UUID


class ConversationUpdateRequest(BaseModel):
    status: ConversationStatus | None = None
    is_ai_paused: bool | None = None
    automation_mode_override: AutomationOverride | None = None
    assigned_user_id: uuid.UUID | None = None
