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
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Instagram Accounts</h1>
          <p className="text-sm text-zinc-500">
            Connect Instagram Professional accounts via official Meta OAuth (no passwords stored).
          </p>
        </div>
        <button
          type="button"
          onClick={handleConnect}
          className="rounded-full bg-[#c8ff00] px-5 py-2.5 text-sm font-semibold text-zinc-950 shadow-xs transition hover:bg-[#b8f000]"
        >
          + Connect Instagram Account
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-700">
          {error}
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-zinc-300 bg-white p-8 text-center text-sm text-zinc-500">
          No accounts connected yet. Click &ldquo;+ Connect Instagram Account&rdquo; to authorize via Meta.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {accounts.map((acc) => (
            <div key={acc.id} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-base font-bold text-zinc-950">@{acc.ig_username}</div>
                  <div className="text-xs text-zinc-500">{acc.account_type}</div>
                </div>
                <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  {acc.connection_status}
                </span>
              </div>

              <div className="flex items-center justify-between text-sm border-t border-zinc-100 pt-3">
                <span className="text-zinc-500">Automation Mode</span>
                <select
                  value={acc.automation_mode}
                  onChange={(e) => changeMode(acc, e.target.value as "auto" | "approval" | "manual")}
                  className="rounded-xl border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-semibold uppercase text-zinc-900"
                >
                  <option value="auto">Auto</option>
                  <option value="approval">Approval</option>
                  <option value="manual">Manual</option>
                </select>
              </div>

              <button
                type="button"
                onClick={() => toggleAgent(acc)}
                className={`w-full rounded-full py-2 text-xs font-semibold transition ${
                  acc.is_agent_enabled
                    ? "bg-[#c8ff00] text-zinc-950 hover:bg-[#b8f000]"
                    : "border border-zinc-200 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
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
