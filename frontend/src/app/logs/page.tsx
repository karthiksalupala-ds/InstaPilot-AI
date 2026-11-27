"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface LogRow {
  id: string;
  created_at: string;
  intent: string | null;
  tools_called: Array<{ name: string }>;
  final_action: string;
  latency_ms: number;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogRow[]>([]);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<LogRow[]>("/logs/agent-executions", auth)
      .then(setLogs)
      .catch(() => undefined);
  }, []);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Activity & Execution Logs</h1>
        <p className="text-sm text-zinc-500">
          Full audit trail of LangGraph runs, tool calls, and delivery status.
        </p>
      </div>

      <div className="rounded-2xl border border-zinc-200 bg-white shadow-xs overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-zinc-50 text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Intent</th>
              <th className="px-4 py-3">Tools Called</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-4 text-xs text-zinc-500">
                  No agent executions logged yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="px-4 py-3 text-xs text-zinc-500">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-medium text-zinc-900">{log.intent ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-indigo-600">
                    {log.tools_called.map((t) => t.name).join(", ") || "none"}
                  </td>
                  <td className="px-4 py-3 text-xs font-semibold uppercase text-zinc-700">{log.final_action}</td>
                  <td className="px-4 py-3 text-xs text-zinc-500">{log.latency_ms}ms</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
