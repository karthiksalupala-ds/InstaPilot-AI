import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.models.instagram import Agent, InstagramAccount
from app.models.knowledge import Product
from app.models.messaging import Conversation
from app.services.agent_graph import run_agent_graph
from app.services.agent_tools import ToolContext, build_agent_tools


class FakeToolChatModel(BaseChatModel):
    """Deterministic fake chat model for testing LangGraph tool loops and guardrails."""

    responses: list[AIMessage]
    _idx: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-tool-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolChatModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        msg = self.responses[min(self._idx, len(self.responses) - 1)]
        self._idx += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])


def _make_account_and_agent() -> tuple[InstagramAccount, Agent, Conversation]:
    ws_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    cust_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    account = InstagramAccount(
        id=acc_id,
        workspace_id=ws_id,
        ig_user_id="17841400001",
        ig_username="urbanthread",
        account_type="BUSINESS",
        connection_status="connected",
        automation_mode="approval",
        is_agent_enabled=True,
        webhook_subscribed=True,
    )
    agent = Agent(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        name="@urbanthread Assistant",
        system_instructions="Be helpful and accurate.",
        personality="helpful",
        communication_style={},
        language_config={"primary": "en", "auto_detect": True},
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        temperature=0.3,
        enabled_tools=[
            "search_knowledge_base",
            "search_products",
            "get_product_details",
            "create_lead",
            "request_human_support",
            "send_instagram_reply",
        ],
        tool_permissions={},
        escalation_config={"keywords": ["lawyer", "scam"]},
    )
    conv = Conversation(
        id=conv_id,
        workspace_id=ws_id,
        instagram_account_id=acc_id,
        customer_id=cust_id,
        channel="dm",
        status="open",
        is_ai_paused=False,
        window_expires_at=datetime.now(UTC) + timedelta(hours=23),
        unread_count=1,
    )
    return account, agent, conv


async def test_tool_allowlist_and_send_guards() -> None:
    mock_db = AsyncMock()
    ctx = ToolContext(
        workspace_id=uuid.uuid4(),
        instagram_account_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        automation_mode="approval",
        window_expires_at=datetime.now(UTC) + timedelta(hours=1),
        db=mock_db,
    )
    tools = build_agent_tools(ctx, ["search_products", "send_instagram_reply"])
    assert [t.name for t in tools] == ["search_products", "send_instagram_reply"]

    send_tool = tools[1]
    res = await send_tool.ainvoke({"text": "Hello"})
    assert "BLOCKED_BY_MODE" in res

    ctx.automation_mode = "auto"
    ctx.window_expires_at = datetime.now(UTC) - timedelta(minutes=5)
    expired_res = await send_tool.ainvoke({"text": "Hello"})
    assert expired_res == "BLOCKED_24H_WINDOW_EXPIRED"


async def test_langgraph_escalates_on_keyword() -> None:
    account, agent, conv = _make_account_and_agent()
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=conv)

    result = await run_agent_graph(
        db=mock_db,
        account=account,
        agent=agent,
        customer_message="This is a scam, I want a real person!",
        conversation=conv,
        chat_model_override=FakeToolChatModel(responses=[AIMessage(content="unused")]),
    )
    assert result["final_action"] == "escalated"
    assert conv.is_ai_paused is True


async def test_langgraph_tool_call_and_grounding_pass() -> None:
    account, agent, conv = _make_account_and_agent()
    product = Product(
        id=uuid.uuid4(),
        workspace_id=account.workspace_id,
        instagram_account_id=account.id,
        sku="HD-BLK-L",
        name="Heavyweight Hoodie",
        description="100% cotton",
        price_cents=189900,
        currency="INR",
        stock_status="in_stock",
        is_active=True,
    )

    class _ScalarResult:
        def all(self):
            return [product]

    mock_db = AsyncMock()
    mock_db.scalars = AsyncMock(return_value=_ScalarResult())

    fake_llm = FakeToolChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "search_products", "args": {"query": "hoodie"}, "id": "tc_1"}],
            ),
            AIMessage(content="The Heavyweight Hoodie is in stock for INR 1899.00!"),
        ]
    )

    result = await run_agent_graph(
        db=mock_db,
        account=account,
        agent=agent,
        customer_message="How much is the hoodie?",
        conversation=conv,
        chat_model_override=fake_llm,
    )
    assert result["grounding_passed"] is True
    assert result["final_action"] == "queued_approval"
    assert result["tools_called"][0]["name"] == "search_products"
    assert conv.ai_summary is not None
    assert "pricing_question" in conv.ai_summary


async def test_grounding_guardrail_blocks_ungrounded_price() -> None:
    account, agent, conv = _make_account_and_agent()
    mock_db = AsyncMock()

    fake_llm = FakeToolChatModel(
        responses=[AIMessage(content="That jacket costs ₹2499!")]
    )
    result = await run_agent_graph(
        db=mock_db,
        account=account,
        agent=agent,
        customer_message="How much is the jacket?",
        conversation=conv,
        chat_model_override=fake_llm,
    )
    assert result["grounding_passed"] is False
    assert result["final_action"] == "escalated"
