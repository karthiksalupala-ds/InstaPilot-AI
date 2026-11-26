"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface IgAccount {
  id: string;
  ig_username: string;
  account_type: string;
  connection_status: string;
  automation_mode: "auto" | "approval" | "manual";
  is_agent_enabled: boolean;
  webhook_subscribed: boolean;
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadAccounts() {
    const auth = getStoredAuth();
    if (!auth) return;
    try {
      const data = await apiFetch<IgAccount[]>("/instagram/accounts", auth);
      setAccounts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load accounts");
    }
  }

  useEffect(() => {
    void loadAccounts();
  }, []);

  async function handleConnect() {
    const auth = getStoredAuth();
    if (!auth) {
      setError("Please sign in first");
      return;
    }
    try {
      const res = await apiFetch<{ authorize_url: string }>("/instagram/oauth/authorize", auth);
      window.location.href = res.authorize_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start OAuth");
    }
  }

  async function toggleAgent(acc: IgAccount) {
    const auth = getStoredAuth();
    if (!auth) return;
    await apiFetch(`/instagram/accounts/${acc.id}`, {
      ...auth,
      method: "PATCH",
      body: JSON.stringify({ is_agent_enabled: !acc.is_agent_enabled }),
    });
    await loadAccounts();
  }

  async function changeMode(acc: IgAccount, mode: "auto" | "approval" | "manual") {
    const auth = getStoredAuth();
    if (!auth) return;
    await apiFetch(`/instagram/accounts/${acc.id}`, {
      ...auth,
      method: "PATCH",
      body: JSON.stringify({ automation_mode: mode }),
    });
    await loadAccounts();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Instagram Account Management</h1>
          <p className="text-sm text-zinc-400">
            Connect Instagram Professional accounts via official Meta OAuth (no passwords stored).
          </p>
        </div>
        <button
          type="button"
          onClick={handleConnect}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          + Connect Instagram Account
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-xs text-rose-300">
          {error}
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-6 text-sm text-zinc-400">
          No accounts connected yet. Click &ldquo;+ Connect Instagram Account&rdquo; to authorize via Meta.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {accounts.map((acc) => (
            <div key={acc.id} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-base font-semibold">@{acc.ig_username}</div>
                  <div className="text-xs text-zinc-400">{acc.account_type}</div>
                </div>
                <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
                  {acc.connection_status}
                </span>
              </div>

              <div className="flex items-center justify-between text-sm border-t border-zinc-800 pt-3">
                <span className="text-zinc-400">Mode</span>
                <select
                  value={acc.automation_mode}
                  onChange={(e) => changeMode(acc, e.target.value as "auto" | "approval" | "manual")}
                  className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs uppercase"
                >
                  <option value="auto">Auto</option>
                  <option value="approval">Approval</option>
                  <option value="manual">Manual</option>
                </select>
              </div>

              <button
                type="button"
                onClick={() => toggleAgent(acc)}
                className={`w-full rounded-lg py-1.5 text-xs font-medium ${
                  acc.is_agent_enabled
                    ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                    : "border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {acc.is_agent_enabled ? "Agent ON (Click to Pause)" : "Agent OFF (Click to Enable)"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
