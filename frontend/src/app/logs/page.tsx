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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activity & Execution Logs</h1>
        <p className="text-sm text-zinc-400">
          Full audit trail of LangGraph runs, tool calls, and delivery status.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-950/60 text-xs uppercase text-zinc-400">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Intent</th>
              <th className="px-4 py-3">Tools Called</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/80">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-4 text-xs text-zinc-400">
                  No agent executions logged yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="px-4 py-3 text-zinc-400">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3">{log.intent ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300">
                    {log.tools_called.map((t) => t.name).join(", ") || "none"}
                  </td>
                  <td className="px-4 py-3 text-xs uppercase">{log.final_action}</td>
                  <td className="px-4 py-3 text-zinc-400">{log.latency_ms}ms</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
