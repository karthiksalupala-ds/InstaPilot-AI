"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface IgAccount {
  id: string;
  ig_username: string;
}

interface RuleRow {
  id: string;
  name: string;
  trigger_type: string;
  is_enabled: boolean;
}

export default function AutomationPage() {
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [rules, setRules] = useState<RuleRow[]>([]);
  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("");
  const [replyText, setReplyText] = useState("");

  async function loadRules(accId: string) {
    const auth = getStoredAuth();
    if (!auth || !accId) return;
    const data = await apiFetch<RuleRow[]>(`/accounts/${accId}/automation-rules`, auth);
    setRules(data);
  }

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<IgAccount[]>("/instagram/accounts", auth)
      .then((list) => {
        setAccounts(list);
        if (list.length > 0) setAccountId(list[0].id);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (accountId) void loadRules(accountId);
  }, [accountId]);

  async function createRule(e: React.FormEvent) {
    e.preventDefault();
    const auth = getStoredAuth();
    if (!auth || !accountId) return;
    await apiFetch(`/accounts/${accountId}/automation-rules`, {
      ...auth,
      method: "POST",
      body: JSON.stringify({
        name,
        trigger_type: "comment_received",
        conditions: { keywords: keyword ? [keyword] : [] },
        actions: { private_reply_dm: replyText },
      }),
    });
    setName("");
    setKeyword("");
    setReplyText("");
    await loadRules(accountId);
  }

  async function deleteRule(ruleId: string) {
    const auth = getStoredAuth();
    if (!auth || !accountId) return;
    await apiFetch(`/accounts/${accountId}/automation-rules/${ruleId}`, {
      ...auth,
      method: "DELETE",
    });
    await loadRules(accountId);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Automation Rules</h1>
          <p className="text-sm text-zinc-400">
            Configure DM & comment triggers, conditions, and Meta-compliant actions per account.
          </p>
        </div>
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm"
        >
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              @{a.ig_username}
            </option>
          ))}
        </select>
      </div>

      <form onSubmit={createRule} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 grid gap-3 sm:grid-cols-3">
        <input
          type="text"
          required
          placeholder="Rule name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Comment keyword (e.g. PRICE)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Private DM reply text"
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!accountId}
          className="sm:col-span-3 w-fit rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          + Create Comment-to-DM Rule
        </button>
      </form>

      <div className="space-y-3">
        {rules.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 text-xs text-zinc-400">
            No automation rules yet.
          </div>
        ) : (
          rules.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div>
                <div className="font-medium">{r.name}</div>
                <div className="text-xs text-zinc-400">Trigger: {r.trigger_type}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">
                  {r.is_enabled ? "Enabled" : "Disabled"}
                </span>
                <button
                  type="button"
                  onClick={() => deleteRule(r.id)}
                  className="text-xs text-rose-400 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
