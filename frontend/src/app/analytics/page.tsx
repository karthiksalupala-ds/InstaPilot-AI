"use client";

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

export default function AnalyticsPage() {
  const [data, setData] = useState<OverviewKPIs | null>(null);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<OverviewKPIs>("/analytics/overview", auth)
      .then(setData)
      .catch(() => undefined);
  }, []);

  const metrics = [
    { label: "Total Messages (30d)", value: String(data?.total_messages ?? 0) },
    { label: "AI Replies Sent", value: String(data?.ai_sent_count ?? 0) },
    { label: "Avg Response Latency", value: `${data?.avg_latency_ms ?? 0}ms` },
    { label: "Total Tokens Used", value: String(data?.total_tokens ?? 0) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-zinc-400">
          Performance, conversion, and LLM usage metrics across accounts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
            <div className="text-xs uppercase text-zinc-400">{m.label}</div>
            <div className="mt-2 text-3xl font-semibold">{m.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
