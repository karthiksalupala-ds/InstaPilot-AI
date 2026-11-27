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
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">AI Agent Management</h1>
        <p className="text-sm text-zinc-500">
          Each connected Instagram account runs an independent, strictly isolated LangGraph agent.
        </p>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-300 bg-white p-8 text-center text-sm text-zinc-500">
          No agents yet. Connect an Instagram account first.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map(({ account, agent }) => (
            <div key={account.id} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-zinc-950">{agent?.name ?? `@${account.ig_username}`}</div>
                  <div className="text-xs text-zinc-500">
                    {agent ? `${agent.llm_provider} — ${agent.llm_model}` : "Default"}
                  </div>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    account.is_agent_enabled
                      ? "bg-[#c8ff00] text-zinc-950"
                      : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  {account.is_agent_enabled ? "ON" : "OFF"}
                </span>
              </div>

              <div className="text-xs text-zinc-500">
                Tools ({agent?.enabled_tools.length ?? 0}):{" "}
                {agent?.enabled_tools.slice(0, 4).join(", ") || "none"}
              </div>

              <Link
                href="/agent-config"
                className="block w-full rounded-full bg-zinc-950 py-2 text-center text-xs font-semibold text-white transition hover:bg-zinc-800"
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
