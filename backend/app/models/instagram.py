import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ig_user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ig_username: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False)
    automation_mode: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    is_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_webhook_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_type: Mapped[str] = mapped_column(String(32), default="long_lived", nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    personality: Mapped[str] = mapped_column(String(64), default="helpful", nullable=False)
    communication_style: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    language_config: Mapped[dict[str, object]] = mapped_column(
        JSON, default=lambda: {"primary": "en", "auto_detect": True}, nullable=False
    )
    llm_provider: Mapped[str] = mapped_column(String(32), default="gemini", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(64), default="gemini-2.5-flash", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    enabled_tools: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    tool_permissions: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    escalation_config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
