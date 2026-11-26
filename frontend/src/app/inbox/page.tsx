"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface ConvItem {
  id: string;
  ig_username: string;
  customer_username: string | null;
  customer_ig_id: string;
  channel: string;
  status: string;
  is_ai_paused: boolean;
  last_intent: string | null;
  unread_count: number;
}

interface MsgItem {
  id: string;
  sender_type: string;
  content: string;
  delivery_status: string;
}

interface ConvDetail {
  id: string;
  ig_username: string;
  is_ai_paused: boolean;
  ai_summary: string | null;
  last_intent: string | null;
  customer: { ig_username: string | null; ig_scoped_user_id: string };
  messages: MsgItem[];
}

export default function InboxPage() {
  const [conversations, setConversations] = useState<ConvItem[]>([]);
  const [active, setActive] = useState<ConvDetail | null>(null);
  const [replyText, setReplyText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadList() {
    const auth = getStoredAuth();
    if (!auth) return;
    const data = await apiFetch<ConvItem[]>("/inbox/conversations", auth);
    setConversations(data);
    if (data.length > 0 && !active) {
      await loadThread(data[0].id);
    }
  }

  async function loadThread(convId: string) {
    const auth = getStoredAuth();
    if (!auth) return;
    const detail = await apiFetch<ConvDetail>(`/inbox/conversations/${convId}`, auth);
    setActive(detail);
  }

  useEffect(() => {
    void loadList().catch(() => undefined);
    const auth = getStoredAuth();
    if (!auth) return;

    const controller = new AbortController();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    fetch(`${apiBase}/events/stream`, {
      headers: {
        Authorization: `Bearer ${auth.accessToken}`,
        "X-Workspace-Id": auth.workspaceId,
      },
      signal: controller.signal,
    })
      .then(async (res) => {
        const reader = res.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          if (chunk.includes("message.received")) {
            void loadList().catch(() => undefined);
          }
        }
      })
      .catch(() => undefined);

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function sendManual() {
    const auth = getStoredAuth();
    if (!auth || !active || !replyText.trim()) return;
    setError(null);
    try {
      await apiFetch(`/inbox/conversations/${active.id}/messages`, {
        ...auth,
        method: "POST",
        body: JSON.stringify({ text: replyText }),
      });
      setReplyText("");
      await loadThread(active.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    }
  }

  async function approveDraft(messageId: string) {
    const auth = getStoredAuth();
    if (!auth || !active) return;
    await apiFetch(`/inbox/conversations/${active.id}/approve-draft`, {
      ...auth,
      method: "POST",
      body: JSON.stringify({ message_id: messageId }),
    });
    await loadThread(active.id);
  }

  async function togglePause() {
    const auth = getStoredAuth();
    if (!auth || !active) return;
    await apiFetch(`/inbox/conversations/${active.id}`, {
      ...auth,
      method: "PATCH",
      body: JSON.stringify({ is_ai_paused: !active.is_ai_paused }),
    });
    await loadThread(active.id);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Unified Inbox</h1>
        <p className="text-sm text-zinc-400">
          Centralized DMs & comment threads with AI summaries, approvals, and human handoff.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-4 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3 space-y-2">
          {conversations.length === 0 ? (
            <div className="p-3 text-xs text-zinc-400">No conversations yet.</div>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => loadThread(c.id)}
                className="w-full text-left rounded-lg border border-zinc-800 bg-zinc-950/70 p-3 hover:border-indigo-500/40"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-zinc-200">
                    {c.customer_username ? `@${c.customer_username}` : c.customer_ig_id}
                  </span>
                  <span className="text-zinc-400">{c.status}</span>
                </div>
                <div className="text-[11px] text-indigo-300">@{c.ig_username} • {c.channel}</div>
              </button>
            ))
          )}
        </div>

        <div className="lg:col-span-5 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 flex flex-col justify-between space-y-4">
          {!active ? (
            <div className="text-sm text-zinc-400">Select a conversation to view messages.</div>
          ) : (
            <>
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <div className="text-sm font-semibold">
                      {active.customer.ig_username ? `@${active.customer.ig_username}` : active.customer.ig_scoped_user_id}
                    </div>
                    <div className="text-xs text-zinc-400">@{active.ig_username}</div>
                  </div>
                  <button
                    type="button"
                    onClick={togglePause}
                    className="rounded-lg border border-zinc-700 px-2.5 py-1 text-xs hover:bg-zinc-800"
                  >
                    {active.is_ai_paused ? "Resume AI" : "Pause AI"}
                  </button>
                </div>

                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {active.messages.map((m) => (
                    <div
                      key={m.id}
                      className={`rounded-lg p-3 text-sm ${
                        m.delivery_status === "pending_approval"
                          ? "border border-indigo-500/30 bg-indigo-500/10"
                          : "bg-zinc-950"
                      }`}
                    >
                      <div className="text-[11px] text-zinc-400 mb-1">{m.sender_type}</div>
                      <div>{m.content}</div>
                      {m.delivery_status === "pending_approval" && (
                        <button
                          type="button"
                          onClick={() => approveDraft(m.id)}
                          className="mt-2 rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-500"
                        >
                          Approve & Send
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 border-t border-zinc-800 pt-3">
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Write a manual reply..."
                  className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
                />
                <button
                  type="button"
                  onClick={sendManual}
                  className="rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-900"
                >
                  Send
                </button>
              </div>
            </>
          )}
        </div>

        <div className="lg:col-span-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-3">
          <h2 className="text-sm font-semibold">Customer & AI Summary</h2>
          <div className="text-xs text-zinc-400">
            Intent: <span className="text-zinc-200">{active?.last_intent ?? "—"}</span>
          </div>
          <p className="text-xs text-zinc-300">{active?.ai_summary ?? "No AI summary yet."}</p>
        </div>
      </div>
    </div>
  );
}
