import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    total_messages: int
    ai_sent_count: int
    pending_approvals: int
    escalated_count: int
    avg_latency_ms: float
    total_leads: int
    converted_leads: int
    total_tokens: int


class AgentExecutionLogResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    conversation_id: uuid.UUID
    intent: str | None
    tools_called: list[dict[str, Any]]
    draft_response: str | None
    final_action: str
    llm_provider: str
    llm_model: str
    tokens_prompt: int
    tokens_completion: int
    latency_ms: int
    error_message: str | None
    created_at: datetime


class NotificationResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID | None
    type: str
    title: str
    body: str
    link_url: str | None
    is_read: bool
    created_at: datetime
