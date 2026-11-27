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
  const [lastPrompt, setLastPrompt] = useState("Hi, what is the price?");
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

  const activeAccount = accounts.find((a) => a.id === accountId);

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
    setLastPrompt(simInput);
    try {
      const res = await apiFetch<SandboxResult>(`/accounts/${accountId}/agent/sandbox`, {
        ...auth,
        method: "POST",
        body: JSON.stringify({ message: simInput }),
      });
      setSimResult(res);
      setSimInput("");
    } finally {
      setSimLoading(false);
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Agent Configuration & Sandbox</h1>
        <p className="text-sm text-zinc-500">
          Customize persona, AI model, and test replies live in the Instagram DM simulator.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-6 rounded-3xl border border-zinc-200 bg-white p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-zinc-950">Agent Identity & Instructions</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-zinc-600">Instagram Account</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
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
                  <label className="text-xs font-medium text-zinc-600">AI Model</label>
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
                    className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
                  >
                    <option value="gemini">Gemini (gemini-2.5-flash)</option>
                    <option value="groq">Groq (llama-3.3-70b-versatile)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-zinc-600">System Instructions</label>
                  <textarea
                    rows={6}
                    value={config.system_instructions}
                    onChange={(e) => setConfig({ ...config, system_instructions: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm"
                  />
                </div>

                <div className="flex items-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={saveConfig}
                    className="rounded-full bg-[#c8ff00] px-5 py-2 text-sm font-semibold text-zinc-950 hover:bg-[#b8f000]"
                  >
                    Save Configuration
                  </button>
                  {savedMsg && <span className="text-xs font-semibold text-emerald-600">{savedMsg}</span>}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="lg:col-span-6 rounded-3xl border border-zinc-200 bg-dot-grid p-6 flex flex-col items-center justify-between space-y-4">
          <div className="w-full max-w-[280px] rounded-[36px] border-[6px] border-zinc-900 bg-zinc-950 p-3 text-white shadow-2xl">
            <div className="mx-auto mb-3 h-1.5 w-16 rounded-full bg-zinc-800" />
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2 px-1">
              <span className="text-xs font-semibold">
                {activeAccount ? `@${activeAccount.ig_username}` : "@sandbox"}
              </span>
              <span className="text-[10px] text-[#c8ff00]">Sandbox</span>
            </div>

            <div className="my-4 space-y-3 min-h-[220px] px-1">
              <div className="flex justify-end">
                <div className="rounded-2xl bg-indigo-600 px-3 py-1.5 text-xs text-white max-w-[85%]">
                  {lastPrompt}
                </div>
              </div>
              {simResult && (
                <>
                  <div className="rounded-2xl bg-zinc-800 px-3 py-2 text-xs text-zinc-100 leading-relaxed">
                    {simResult.draft_response}
                  </div>
                  <div className="text-[10px] text-zinc-400 px-1">
                    {simResult.intent} • {simResult.grounding_passed ? "Grounded" : "Blocked"} • {simResult.latency_ms}ms
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="flex w-full gap-2">
            <input
              type="text"
              value={simInput}
              onChange={(e) => setSimInput(e.target.value)}
              placeholder="Type a simulated customer DM..."
              className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm shadow-xs"
            />
            <button
              type="button"
              disabled={simLoading || !accountId}
              onClick={runSandbox}
              className="rounded-full bg-zinc-950 px-5 py-2 text-xs font-semibold text-white hover:bg-zinc-800 disabled:opacity-50"
            >
              {simLoading ? "Running..." : "Test"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
