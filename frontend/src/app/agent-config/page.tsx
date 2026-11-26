"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface IgAccount {
  id: string;
  ig_username: string;
}

interface AgentConfig {
  id: string;
  name: string;
  system_instructions: string;
  personality: string;
  llm_provider: "gemini" | "groq";
  llm_model: string;
  temperature: number;
  enabled_tools: string[];
}

interface SandboxResult {
  intent: string;
  tools_called: Array<{ name: string; args: Record<string, unknown> }>;
  draft_response: string;
  grounding_passed: boolean;
  final_action: string;
  latency_ms: number;
}

export default function AgentConfigPage() {
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [accountId, setAccountId] = useState<string>("");
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [simInput, setSimInput] = useState("");
  const [simResult, setSimResult] = useState<SandboxResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);

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
    const auth = getStoredAuth();
    if (!auth || !accountId) return;
    apiFetch<AgentConfig>(`/accounts/${accountId}/agent`, auth)
      .then(setConfig)
      .catch(() => undefined);
  }, [accountId]);

  async function saveConfig() {
    const auth = getStoredAuth();
    if (!auth || !accountId || !config) return;
    setSavedMsg(null);
    await apiFetch<AgentConfig>(`/accounts/${accountId}/agent`, {
      ...auth,
      method: "PATCH",
      body: JSON.stringify({
        name: config.name,
        system_instructions: config.system_instructions,
        llm_provider: config.llm_provider,
        llm_model: config.llm_model,
      }),
    });
    setSavedMsg("Saved!");
  }

  async function runSandbox() {
    const auth = getStoredAuth();
    if (!auth || !accountId || !simInput.trim()) return;
    setSimLoading(true);
    try {
      const res = await apiFetch<SandboxResult>(`/accounts/${accountId}/agent/sandbox`, {
        ...auth,
        method: "POST",
        body: JSON.stringify({ message: simInput }),
      });
      setSimResult(res);
    } finally {
      setSimLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agent Configuration & Sandbox</h1>
        <p className="text-sm text-zinc-400">
          Customize persona, LLM provider, and test replies safely without sending to Instagram.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 space-y-4">
          <h2 className="text-base font-semibold">Agent Identity & Instructions</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-zinc-400">Instagram Account</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
              >
                {accounts.length === 0 ? (
                  <option value="">No accounts connected</option>
                ) : (
                  accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      @{a.ig_username}
                    </option>
                  ))
                )}
              </select>
            </div>

            {config && (
              <>
                <div>
                  <label className="text-xs text-zinc-400">LLM Provider</label>
                  <select
                    value={config.llm_provider}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        llm_provider: e.target.value as "gemini" | "groq",
                        llm_model:
                          e.target.value === "gemini"
                            ? "gemini-2.5-flash"
                            : "llama-3.3-70b-versatile",
                      })
                    }
                    className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
                  >
                    <option value="gemini">Gemini (gemini-2.5-flash)</option>
                    <option value="groq">Groq (llama-3.3-70b-versatile)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-zinc-400">System Instructions</label>
                  <textarea
                    rows={5}
                    value={config.system_instructions}
                    onChange={(e) => setConfig({ ...config, system_instructions: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={saveConfig}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                  >
                    Save Configuration
                  </button>
                  {savedMsg && <span className="text-xs text-emerald-400">{savedMsg}</span>}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 flex flex-col justify-between space-y-4">
          <div>
            <h2 className="text-base font-semibold">Live Sandbox Preview</h2>
            <p className="text-xs text-zinc-400">
              Dry-run against this account&apos;s RAG & tools with zero real Instagram sends.
            </p>
            <div className="mt-4 space-y-2 rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm min-h-40">
              {!simResult ? (
                <div className="text-xs text-zinc-500">Send a simulated message below to test.</div>
              ) : (
                <>
                  <div className="text-xs text-zinc-400">
                    Intent: <span className="text-indigo-300">{simResult.intent}</span> • Grounding:{" "}
                    <span className={simResult.grounding_passed ? "text-emerald-400" : "text-amber-400"}>
                      {simResult.grounding_passed ? "PASSED" : "BLOCKED"}
                    </span>{" "}
                    • {simResult.latency_ms}ms
                  </div>
                  <div className="text-xs font-mono text-zinc-400">
                    Tools: {simResult.tools_called.map((t) => t.name).join(", ") || "none"}
                  </div>
                  <div className="pt-2 text-zinc-100">{simResult.draft_response}</div>
                </>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={simInput}
              onChange={(e) => setSimInput(e.target.value)}
              placeholder="Type a simulated customer DM..."
              className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
            />
            <button
              type="button"
              disabled={simLoading || !accountId}
              onClick={runSandbox}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium hover:bg-zinc-800 disabled:opacity-50"
            >
              {simLoading ? "Running..." : "Test"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
