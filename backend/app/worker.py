import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import httpx
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.redis import create_redis_client
from app.db.session import AsyncSessionLocal
from app.models.instagram import Agent, InstagramAccount, OAuthToken
from app.models.knowledge import KnowledgeDocument
from app.models.messaging import Conversation, Customer
from app.models.operations import Notification
from app.services.agent_graph import run_agent_graph
from app.services.automation_engine import evaluate_automation_rules
from app.services.instagram_messaging import MetaInstagramMessagingClient, check_account_rate_limit
from app.services.instagram_oauth import MetaInstagramOAuthClient
from app.services.rag_service import index_knowledge_document
from app.services.webhook_processor import NormalizedWebhookEvent, ingest_instagram_event


async def index_knowledge_document_job(ctx: dict[str, Any], document_id: str) -> int:
    """ARQ background job: chunk, embed, and store vectors for a KnowledgeDocument."""
    doc_uuid = uuid.UUID(document_id)
    async with AsyncSessionLocal() as db:
        doc = await db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_uuid))
        if doc is None:
            return 0
        return await index_knowledge_document(db, doc)


async def process_instagram_event(ctx: dict[str, Any], event_data: dict[str, Any]) -> str | None:
    """ARQ background job: persist incoming IG event and run LangGraph agent if enabled."""
    event = NormalizedWebhookEvent(**event_data)
    redis_client = create_redis_client()
    try:
        async with AsyncSessionLocal() as db:
            msg = await ingest_instagram_event(db, redis_client, event)
            if msg is None:
                return None

            row = (
                await db.execute(
                    select(InstagramAccount, Agent, Conversation)
                    .join(Agent, Agent.instagram_account_id == InstagramAccount.id)
                    .join(Conversation, Conversation.id == msg.conversation_id)
                    .where(InstagramAccount.id == msg.instagram_account_id)
                )
            ).first()
            if row is not None:
                account, agent, conversation = row
                token_row = await db.scalar(
                    select(OAuthToken).where(OAuthToken.instagram_account_id == account.id)
                )
                customer = await db.scalar(
                    select(Customer).where(Customer.id == conversation.customer_id)
                )
                messaging_client = MetaInstagramMessagingClient()
                access_token = (
                    decrypt_token(token_row.encrypted_access_token) if token_row else None
                )

                if customer is not None:
                    await evaluate_automation_rules(
                        db=db,
                        account=account,
                        conversation=conversation,
                        customer=customer,
                        message=msg,
                        access_token=access_token,
                        messaging_client=messaging_client,
                    )

                if account.is_agent_enabled and not conversation.is_ai_paused and conversation.channel == "dm":
                    async def _send_reply(text: str) -> None:
                        if access_token is None or customer is None:
                            return
                        allowed = await check_account_rate_limit(
                            redis_client, str(account.id), action="send_dm"
                        )
                        if not allowed:
                            return
                        await messaging_client.send_dm(
                            ig_user_id=account.ig_user_id,
                            recipient_igsid=customer.ig_scoped_user_id,
                            text=text,
                            access_token=access_token,
                        )

                    await run_agent_graph(
                        db=db,
                        account=account,
                        agent=agent,
                        customer_message=msg.content,
                        conversation=conversation,
                        trigger_message=msg,
                        is_sandbox=False,
                        send_callback=_send_reply,
                    )
            return str(msg.id)
    finally:
        await redis_client.aclose()


async def refresh_expiring_tokens(ctx: dict[str, Any]) -> int:
    """Daily cron: refresh 60-day tokens that are >24h old and expire within 14 days."""
    now = datetime.now(UTC)
    refresh_before = now + timedelta(days=14)
    min_age = now - timedelta(hours=24)
    refreshed_count = 0
    client = MetaInstagramOAuthClient()

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(InstagramAccount, OAuthToken)
                .join(OAuthToken, OAuthToken.instagram_account_id == InstagramAccount.id)
                .where(
                    OAuthToken.expires_at <= refresh_before,
                    OAuthToken.expires_at > now,
                    OAuthToken.issued_at <= min_age,
                )
            )
        ).all()

        for account, token_row in rows:
            try:
                resp = await client.refresh_long_lived_token(
                    decrypt_token(token_row.encrypted_access_token)
                )
                expires_in = int(resp.get("expires_in", 5183944))
                token_row.encrypted_access_token = encrypt_token(str(resp["access_token"]))
                token_row.issued_at = now
                token_row.expires_at = now + timedelta(seconds=expires_in)
                token_row.last_refreshed_at = now
                account.connection_status = "connected"
                refreshed_count += 1
            except (httpx.HTTPError, ValueError) as exc:
                account.connection_status = "token_expiring"
                db.add(
                    Notification(
                        workspace_id=account.workspace_id,
                        instagram_account_id=account.id,
                        type="token_expiring",
                        title=f"Token refresh failed for @{account.ig_username}",
                        body=f"Automatic refresh failed ({exc}). Please reconnect the account.",
                        link_url="/accounts",
                    )
                )
        await db.commit()
    return refreshed_count


class WorkerSettings:
    """ARQ background worker configuration."""

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    cron_jobs: ClassVar[list[Any]] = [cron(refresh_expiring_tokens, hour=3, minute=0)]
    functions: ClassVar[list[Any]] = [
        process_instagram_event,
        index_knowledge_document_job,
        refresh_expiring_tokens,
    ]
