export interface IgAccountMock {
  id: string;
  handle: string;
  accountType: "BUSINESS" | "MEDIA_CREATOR";
  status: "connected" | "token_expiring" | "disconnected";
  agentEnabled: boolean;
  automationMode: "auto" | "approval" | "manual";
  llmModel: string;
  unread: number;
}

export const MOCK_ACCOUNTS: IgAccountMock[] = [
  {
    id: "acc-1",
    handle: "@urbanthread.store",
    accountType: "BUSINESS",
    status: "connected",
    agentEnabled: true,
    automationMode: "approval",
    llmModel: "gemini-2.5-flash",
    unread: 2,
  },
  {
    id: "acc-2",
    handle: "@glowlab.skincare",
    accountType: "BUSINESS",
    status: "connected",
    agentEnabled: true,
    automationMode: "auto",
    llmModel: "llama-3.3-70b-versatile",
    unread: 1,
  },
  {
    id: "acc-3",
    handle: "@fitcoach.karthik",
    accountType: "MEDIA_CREATOR",
    status: "token_expiring",
    agentEnabled: false,
    automationMode: "manual",
    llmModel: "gemini-2.5-flash",
    unread: 0,
  },
];

export const MOCK_CONVERSATIONS = [
  {
    id: "conv-1",
    account: "@urbanthread.store",
    customer: "@rohan_m",
    intent: "pricing_question",
    mode: "approval",
    status: "pending_human",
    lastMessage: "Do you have the Oversized Heavyweight Hoodie in Black L? Price?",
    aiDraft:
      "Hi Rohan! Our Oversized Heavyweight Hoodie in Black (Size L) is in stock for ₹1,899. Would you like me to share the product link?",
    time: "2m ago",
  },
  {
    id: "conv-2",
    account: "@glowlab.skincare",
    customer: "@ananya.s",
    intent: "product_inquiry",
    mode: "auto",
    status: "open",
    lastMessage: "Is the Vitamin C Serum safe for sensitive skin?",
    aiDraft:
      "Yes! Our 10% Vitamin C Serum is fragrance-free and formulated for sensitive skin. We still recommend a quick patch test first.",
    time: "9m ago",
  },
];
