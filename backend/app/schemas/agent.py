import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    name: str
    system_instructions: str
    personality: str
    communication_style: dict[str, Any]
    language_config: dict[str, Any]
    llm_provider: str
    llm_model: str
    temperature: float
    enabled_tools: list[str]
    escalation_config: dict[str, Any]


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    system_instructions: str | None = None
    personality: str | None = None
    communication_style: dict[str, Any] | None = None
    language_config: dict[str, Any] | None = None
    llm_provider: Literal["gemini", "groq"] | None = None
    llm_model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled_tools: list[str] | None = None
    escalation_config: dict[str, Any] | None = None


class SandboxRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class SandboxResponse(BaseModel):
    intent: str
    tools_called: list[dict[str, Any]]
    draft_response: str
    grounding_passed: bool
    final_action: str
    latency_ms: int
