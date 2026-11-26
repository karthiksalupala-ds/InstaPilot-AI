from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instagram import InstagramAccount
from app.models.messaging import Conversation, Customer, Message
from app.models.operations import AutomationRule, Lead
from app.services.instagram_messaging import MetaInstagramMessagingClient


def _rule_matches(rule: AutomationRule, message: Message, channel: str) -> bool:
    if rule.trigger_type == "dm_received" and channel != "dm":
        return False
    if rule.trigger_type == "comment_received" and channel != "comment_thread":
        return False

    conditions = rule.conditions or {}
    req_channel = conditions.get("channel")
    if req_channel and req_channel != channel:
        return False

    keywords = conditions.get("keywords", [])
    if isinstance(keywords, list) and keywords:
        lowered = message.content.lower()
        if not any(str(kw).lower() in lowered for kw in keywords):
            return False

    return True


async def evaluate_automation_rules(
    *,
    db: AsyncSession,
    account: InstagramAccount,
    conversation: Conversation,
    customer: Customer,
    message: Message,
    access_token: str | None,
    messaging_client: MetaInstagramMessagingClient,
) -> list[str]:
    """Evaluate account-level AutomationRules and execute matched Meta/CRM actions."""
    rules = (
        await db.scalars(
            select(AutomationRule)
            .where(
                AutomationRule.instagram_account_id == account.id,
                AutomationRule.is_enabled.is_(True),
            )
            .order_by(AutomationRule.priority.asc())
        )
    ).all()

    executed_actions: list[str] = []
    comment_id = str((message.metadata_json or {}).get("comment_id", ""))

    for rule in rules:
        if not _rule_matches(rule, message, conversation.channel):
            continue

        actions: dict[str, Any] = rule.actions or {}

        if access_token and conversation.channel == "comment_thread" and comment_id:
            public_text = actions.get("public_comment_reply")
            if isinstance(public_text, str) and public_text.strip():
                await messaging_client.reply_to_comment(
                    comment_id=comment_id,
                    text=public_text,
                    access_token=access_token,
                )
                executed_actions.append(f"rule:{rule.id}:public_comment_reply")

            private_dm_text = actions.get("private_reply_dm")
            if isinstance(private_dm_text, str) and private_dm_text.strip():
                await messaging_client.send_private_reply(
                    ig_user_id=account.ig_user_id,
                    comment_id=comment_id,
                    text=private_dm_text,
                    access_token=access_token,
                )
                executed_actions.append(f"rule:{rule.id}:private_reply_dm")

        if access_token and conversation.channel == "dm":
            auto_dm_text = actions.get("auto_reply_dm")
            if isinstance(auto_dm_text, str) and auto_dm_text.strip():
                await messaging_client.send_dm(
                    ig_user_id=account.ig_user_id,
                    recipient_igsid=customer.ig_scoped_user_id,
                    text=auto_dm_text,
                    access_token=access_token,
                )
                executed_actions.append(f"rule:{rule.id}:auto_reply_dm")

        lead_interest = actions.get("create_lead_interest")
        if isinstance(lead_interest, str) and lead_interest.strip():
            existing = await db.scalar(
                select(Lead).where(
                    Lead.instagram_account_id == account.id,
                    Lead.customer_id == customer.id,
                    Lead.status.in_(["new", "qualified", "contacted"]),
                )
            )
            if existing is None:
                db.add(
                    Lead(
                        workspace_id=account.workspace_id,
                        instagram_account_id=account.id,
                        customer_id=customer.id,
                        conversation_id=conversation.id,
                        status="new",
                        interest_category=lead_interest[:100],
                        notes=f"Auto-created by rule '{rule.name}'",
                    )
                )
                executed_actions.append(f"rule:{rule.id}:create_lead")

        if actions.get("pause_ai") is True:
            conversation.is_ai_paused = True
            executed_actions.append(f"rule:{rule.id}:pause_ai")

    if executed_actions:
        await db.commit()

    return executed_actions
