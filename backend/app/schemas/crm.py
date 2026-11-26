import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

LeadStatus = Literal["new", "qualified", "contacted", "converted", "lost"]
RuleTriggerType = Literal["dm_received", "comment_received", "keyword_match"]


class LeadCreateRequest(BaseModel):
    instagram_account_id: uuid.UUID
    customer_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    status: LeadStatus = "new"
    interest_category: str | None = Field(default=None, max_length=100)
    estimated_value_cents: int | None = Field(default=None, ge=0)
    notes: str | None = None
    follow_up_at: datetime | None = None
    assigned_user_id: uuid.UUID | None = None


class LeadUpdateRequest(BaseModel):
    status: LeadStatus | None = None
    interest_category: str | None = Field(default=None, max_length=100)
    estimated_value_cents: int | None = Field(default=None, ge=0)
    notes: str | None = None
    follow_up_at: datetime | None = None
    assigned_user_id: uuid.UUID | None = None


class LeadResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    instagram_account_id: uuid.UUID
    customer_id: uuid.UUID
    conversation_id: uuid.UUID | None
    status: str
    interest_category: str | None
    estimated_value_cents: int | None
    notes: str | None
    follow_up_at: datetime | None
    assigned_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class AutomationRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    trigger_type: RuleTriggerType
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=1, le=1000)
    is_enabled: bool = True


class AutomationRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    trigger_type: RuleTriggerType | None = None
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)
    is_enabled: bool | None = None


class AutomationRuleResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    name: str
    trigger_type: str
    conditions: dict[str, Any]
    actions: dict[str, Any]
    priority: int
    is_enabled: bool
    created_at: datetime
