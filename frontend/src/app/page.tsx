"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface OverviewKPIs {
  total_messages: number;
  ai_sent_count: number;
  pending_approvals: number;
  escalated_count: number;
  avg_latency_ms: number;
  total_leads: number;
  converted_leads: number;
  total_tokens: number;
}

interface IgAccount {
  id: string;
  ig_username: string;
  automation_mode: string;
  is_agent_enabled: boolean;
  connection_status: string;
}

export default function OverviewPage() {
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [signedIn, setSignedIn] = useState(true);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) {
      setSignedIn(false);
      return;
    }
    Promise.all([
      apiFetch<OverviewKPIs>("/analytics/overview", auth),
      apiFetch<IgAccount[]>("/instagram/accounts", auth),
    ])
      .then(([kpiData, accData]) => {
        setKpis(kpiData);
        setAccounts(accData);
      })
      .catch(() => setSignedIn(false));
  }, []);

  if (!signedIn) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-8 text-center space-y-3">
        <h1 className="text-xl font-semibold">Welcome to InstaPilot AI</h1>
        <p className="text-sm text-zinc-400">
          Sign in or initialize your owner workspace to view live account metrics.
        </p>
        <Link
          href="/login"
          className="inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Sign In / Initialize
        </Link>
      </div>
    );
  }

  const cards = [
    { label: "Connected Accounts", value: String(accounts.length), sub: `${accounts.filter((a) => a.is_agent_enabled).length} agents active` },
    { label: "Messages (30d)", value: String(kpis?.total_messages ?? 0), sub: `${kpis?.ai_sent_count ?? 0} AI replies sent` },
    { label: "Pending Approvals", value: String(kpis?.pending_approvals ?? 0), sub: `${kpis?.escalated_count ?? 0} escalated` },
    { label: "Leads Captured", value: String(kpis?.total_leads ?? 0), sub: `${kpis?.converted_leads ?? 0} converted` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview Dashboard</h1>
        <p className="text-sm text-zinc-400">
          Live status across all connected Instagram accounts and AI agents.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((s) => (
          <div key={s.label} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-zinc-400">{s.label}</div>
            <div className="mt-2 text-3xl font-semibold">{s.value}</div>
            <div className="mt-1 text-xs text-zinc-400">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
        <h2 className="text-base font-semibold">Account Health & Agent Status</h2>
        {accounts.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-400">
            No Instagram accounts connected yet. Go to{" "}
            <Link href="/accounts" className="text-indigo-400 underline">
              Instagram Accounts
            </Link>{" "}
            to connect one.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="flex items-center justify-between rounded-lg border border-zinc-800/80 bg-zinc-950/60 px-4 py-3"
              >
                <div>
                  <div className="text-sm font-medium">@{acc.ig_username}</div>
                  <div className="text-xs text-zinc-400">
                    Mode: <span className="uppercase">{acc.automation_mode}</span> • Status: {acc.connection_status}
                  </div>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    acc.is_agent_enabled
                      ? "bg-emerald-500/15 text-emerald-300"
                      : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {acc.is_agent_enabled ? "Agent ON" : "Agent OFF"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
