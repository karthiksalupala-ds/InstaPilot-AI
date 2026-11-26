"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface IgAccount {
  id: string;
  ig_username: string;
  is_agent_enabled: boolean;
  automation_mode: string;
}

interface AgentInfo {
  name: string;
  llm_provider: string;
  llm_model: string;
  enabled_tools: string[];
}

export default function AgentsPage() {
  const [items, setItems] = useState<Array<{ account: IgAccount; agent: AgentInfo | null }>>([]);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<IgAccount[]>("/instagram/accounts", auth)
      .then(async (accounts) => {
        const loaded = await Promise.all(
          accounts.map(async (account) => {
            try {
              const agent = await apiFetch<AgentInfo>(`/accounts/${account.id}/agent`, auth);
              return { account, agent };
            } catch {
              return { account, agent: null };
            }
          })
        );
        setItems(loaded);
      })
      .catch(() => undefined);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Agent Management</h1>
        <p className="text-sm text-zinc-400">
          Each connected Instagram account runs an independent, strictly isolated LangGraph agent.
        </p>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-6 text-sm text-zinc-400">
          No agents yet. Connect an Instagram account first.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map(({ account, agent }) => (
            <div key={account.id} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{agent?.name ?? `@${account.ig_username}`}</div>
                  <div className="text-xs text-zinc-400">
                    {agent ? `${agent.llm_provider} — ${agent.llm_model}` : "Default"}
                  </div>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs ${
                    account.is_agent_enabled
                      ? "bg-emerald-500/15 text-emerald-300"
                      : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {account.is_agent_enabled ? "ON" : "OFF"}
                </span>
              </div>

              <div className="text-xs text-zinc-400">
                Tools ({agent?.enabled_tools.length ?? 0}):{" "}
                {agent?.enabled_tools.slice(0, 4).join(", ") || "none"}
              </div>

              <Link
                href="/agent-config"
                className="block w-full rounded-lg border border-zinc-700 py-2 text-center text-xs font-medium hover:bg-zinc-800"
              >
                Configure Agent & Sandbox
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
