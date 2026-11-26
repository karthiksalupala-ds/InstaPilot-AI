from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import publish_workspace_event
from app.models.instagram import InstagramAccount
from app.models.messaging import Conversation, Customer, Message


@dataclass(frozen=True)
class NormalizedWebhookEvent:
    ig_account_user_id: str
    external_event_id: str
    sender_ig_id: str
    sender_username: str | None
    channel: str  # "dm" | "comment_thread"
    message_type: str  # "text" | "image" | "comment"
    content: str
    media_url: str | None
    metadata: dict[str, Any]


def extract_normalized_events(payload: dict[str, Any]) -> list[NormalizedWebhookEvent]:
    """Parse Meta Instagram webhook JSON into normalized DM and comment events."""
    if payload.get("object") != "instagram":
        return []

    events: list[NormalizedWebhookEvent] = []
    for entry in payload.get("entry", []):
        entry_id = str(entry.get("id", ""))

        # 1. Direct Messages & story replies
        for msg_event in entry.get("messaging", []):
            message = msg_event.get("message")
            if not message or message.get("is_echo"):
                continue
            sender_id = str(msg_event.get("sender", {}).get("id", ""))
            recipient_id = str(msg_event.get("recipient", {}).get("id", entry_id))
            mid = str(message.get("mid", ""))
            if not sender_id or not mid or sender_id == recipient_id:
                continue

            text = str(message.get("text") or "")
            attachments = message.get("attachments", [])
            media_url = None
            msg_type = "text"
            if attachments:
                first_att = attachments[0]
                media_url = first_att.get("payload", {}).get("url")
                msg_type = str(first_att.get("type", "image"))
                if not text:
                    text = f"[{msg_type} attachment]"

            events.append(
                NormalizedWebhookEvent(
                    ig_account_user_id=recipient_id,
                    external_event_id=mid,
                    sender_ig_id=sender_id,
                    sender_username=None,
                    channel="dm",
                    message_type=msg_type,
                    content=text,
                    media_url=media_url,
                    metadata={"raw_timestamp": msg_event.get("timestamp")},
                )
            )

        # 2. Comments on posts / reels
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            val = change.get("value", {})
            comment_id = str(val.get("id", ""))
            from_obj = val.get("from", {})
            sender_id = str(from_obj.get("id", ""))
            if not comment_id or not sender_id or sender_id == entry_id:
                continue

            events.append(
                NormalizedWebhookEvent(
                    ig_account_user_id=entry_id,
                    external_event_id=f"comment:{comment_id}",
                    sender_ig_id=sender_id,
                    sender_username=from_obj.get("username"),
                    channel="comment_thread",
                    message_type="comment",
                    content=str(val.get("text", "")),
                    media_url=None,
                    metadata={
                        "comment_id": comment_id,
                        "media_id": val.get("media", {}).get("id"),
                    },
                )
            )

    return events


async def ingest_instagram_event(
    db: AsyncSession,
    redis_client: aioredis.Redis,
    event: NormalizedWebhookEvent,
) -> Message | None:
    """Persist an incoming Instagram DM or comment and publish an SSE update."""
    account = await db.scalar(
        select(InstagramAccount).where(InstagramAccount.ig_user_id == event.ig_account_user_id)
    )
    if account is None:
        return None

    existing_msg = await db.scalar(
        select(Message).where(Message.external_message_id == event.external_event_id)
    )
    if existing_msg is not None:
        return None

    now = datetime.now(UTC)
    account.last_webhook_at = now

    customer = await db.scalar(
        select(Customer).where(
            Customer.instagram_account_id == account.id,
            Customer.ig_scoped_user_id == event.sender_ig_id,
        )
    )
    if customer is None:
        customer = Customer(
            workspace_id=account.workspace_id,
            instagram_account_id=account.id,
            ig_scoped_user_id=event.sender_ig_id,
            ig_username=event.sender_username,
        )
        db.add(customer)
        await db.flush()
    else:
        customer.last_interaction_at = now
        if event.sender_username and not customer.ig_username:
            customer.ig_username = event.sender_username

    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.instagram_account_id == account.id,
            Conversation.customer_id == customer.id,
            Conversation.channel == event.channel,
        )
    )
    window_delta = timedelta(hours=24) if event.channel == "dm" else timedelta(days=7)
    if conversation is None:
        conversation = Conversation(
            workspace_id=account.workspace_id,
            instagram_account_id=account.id,
            customer_id=customer.id,
            channel=event.channel,
            status="open",
            window_expires_at=now + window_delta,
            unread_count=1,
            last_message_at=now,
        )
        db.add(conversation)
        await db.flush()
    else:
        conversation.window_expires_at = now + window_delta
        conversation.unread_count += 1
        conversation.last_message_at = now

    message = Message(
        workspace_id=account.workspace_id,
        instagram_account_id=account.id,
        conversation_id=conversation.id,
        external_message_id=event.external_event_id,
        sender_type="customer",
        message_type=event.message_type,
        content=event.content,
        media_url=event.media_url,
        delivery_status="received",
        metadata_json=event.metadata,
    )
    db.add(message)
    await db.commit()

    await publish_workspace_event(
        redis_client,
        str(account.workspace_id),
        "message.received",
        {
            "instagram_account_id": str(account.id),
            "ig_username": account.ig_username,
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "channel": event.channel,
            "content": event.content,
        },
    )
    return message
