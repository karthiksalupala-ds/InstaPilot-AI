"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Bot, Inbox, Instagram, Sparkles, UserCheck } from "lucide-react";
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
  account_type: string;
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
      <div className="mx-auto mt-10 max-w-xl rounded-3xl border border-zinc-200 bg-white p-10 text-center shadow-sm space-y-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#c8ff00] text-zinc-950">
          <Sparkles className="h-6 w-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">
          Welcome to InstaPilot AI
        </h1>
        <p className="text-sm text-zinc-500">
          Sign in or initialize your owner workspace to connect Instagram accounts and launch your AI agents.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-zinc-800"
        >
          Sign In / Get Started
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  const cards = [
    { label: "Connected Accounts", value: String(accounts.length), sub: `${accounts.filter((a) => a.is_agent_enabled).length} agents active`, icon: Instagram },
    { label: "Messages (30d)", value: String(kpis?.total_messages ?? 0), sub: `${kpis?.ai_sent_count ?? 0} AI replies sent`, icon: Inbox },
    { label: "Pending Approvals", value: String(kpis?.pending_approvals ?? 0), sub: `${kpis?.escalated_count ?? 0} escalated`, icon: Bot },
    { label: "Leads Captured", value: String(kpis?.total_leads ?? 0), sub: `${kpis?.converted_leads ?? 0} converted`, icon: UserCheck },
  ];

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950">
            Hey{accounts[0] ? ` @${accounts[0].ig_username}` : ""}!
          </h1>
          <p className="text-sm text-zinc-500">
            Manage your connected Instagram AI agents, automations, and live DMs.
          </p>
        </div>
        <Link
          href="/inbox"
          className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-5 py-2.5 text-xs font-semibold text-white transition hover:bg-zinc-800"
        >
          Open Unified Inbox
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="rounded-2xl border border-zinc-200/90 bg-white p-5 shadow-xs transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-500">{s.label}</span>
                <span className="rounded-xl bg-zinc-100 p-2 text-zinc-700">
                  <Icon className="h-4 w-4" />
                </span>
              </div>
              <div className="mt-3 text-3xl font-bold tracking-tight text-zinc-950">{s.value}</div>
              <div className="mt-1 text-xs text-zinc-500">{s.sub}</div>
            </div>
          );
        })}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight text-zinc-950">Connected Accounts</h2>
          <Link href="/accounts" className="text-xs font-semibold text-zinc-600 hover:text-zinc-950">
            Manage all →
          </Link>
        </div>

        {accounts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-300 bg-white p-8 text-center text-sm text-zinc-500">
            No Instagram accounts connected yet.{" "}
            <Link href="/accounts" className="font-semibold text-zinc-950 underline">
              Connect your first account
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs transition hover:shadow-md space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-base font-bold text-zinc-950">@{acc.ig_username}</div>
                    <div className="text-xs text-zinc-500">
                      {acc.account_type} • {acc.automation_mode.toUpperCase()} mode
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      acc.is_agent_enabled
                        ? "bg-[#c8ff00] text-zinc-950"
                        : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {acc.is_agent_enabled ? "Agent ON" : "Agent OFF"}
                  </span>
                </div>

                <div className="flex gap-2">
                  <Link
                    href="/automation"
                    className="flex-1 rounded-full bg-zinc-950 py-2 text-center text-xs font-semibold text-white transition hover:bg-zinc-800"
                  >
                    Set up Automation
                  </Link>
                  <Link
                    href="/agent-config"
                    className="rounded-full border border-zinc-200 px-3.5 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50"
                  >
                    Sandbox
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
