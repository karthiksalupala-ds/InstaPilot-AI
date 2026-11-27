"use client";

import { useEffect, useState } from "react";
import { Play, Sparkles, Trash2 } from "lucide-react";
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

const TEMPLATES = [
  {
    category: "Sell & earn",
    title: "Send link on keyword",
    desc: 'Someone comments "LINK" -> they get your link in DMs.',
    keyword: "link",
    userMsg: "Need the LINK please!",
    reply: "Here's your link! Tap below to check it out.",
  },
  {
    category: "Sell & earn",
    title: "Share pricing info",
    desc: 'Someone comments "PRICE" -> they get your rates automatically.',
    keyword: "price",
    userMsg: "What's the PRICE?",
    reply: "Here are our current plans & pricing details!",
  },
  {
    category: "Capture leads",
    title: "Deliver lead magnets",
    desc: 'Someone comments "FREE" -> send your PDF or guide in DM.',
    keyword: "free",
    userMsg: "Send me the FREE guide!",
    reply: "Your free guide is ready! Here is the download link.",
  },
  {
    category: "Engage audience",
    title: "Thank commenters",
    desc: 'Someone comments a keyword -> send a personal thank you DM.',
    keyword: "love",
    userMsg: "Love this! AMAZING content!",
    reply: "Thanks so much! Means a lot!",
  },
];

const SUGGESTED_KEYWORDS = ["link", "shop", "order", "buy", "price", "discount", "info", "details"];

export default function AutomationPage() {
  const [tab, setTab] = useState<"builder" | "templates">("builder");
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [rules, setRules] = useState<RuleRow[]>([]);

  const [name, setName] = useState("Send link on keyword");
  const [keywords, setKeywords] = useState<string[]>(["link"]);
  const [customKw, setCustomKw] = useState("");
  const [replyText, setReplyText] = useState("Here's your link! Let me know if you have any questions.");
  const [saving, setSaving] = useState(false);

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

  const activeAccount = accounts.find((a) => a.id === accountId);

  function toggleKeyword(kw: string) {
    setKeywords((prev) => (prev.includes(kw) ? prev.filter((k) => k !== kw) : [...prev, kw]));
  }

  function addCustomKeyword() {
    const trimmed = customKw.trim().toLowerCase();
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
    }
    setCustomKw("");
  }

  async function startAutomation() {
    const auth = getStoredAuth();
    if (!auth || !accountId || !replyText.trim()) return;
    setSaving(true);
    try {
      await apiFetch(`/accounts/${accountId}/automation-rules`, {
        ...auth,
        method: "POST",
        body: JSON.stringify({
          name: name || "Keyword Automation",
          trigger_type: "comment_received",
          conditions: { keywords },
          actions: { private_reply_dm: replyText },
        }),
      });
      await loadRules(accountId);
    } finally {
      setSaving(false);
    }
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
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 rounded-full border border-zinc-200 bg-white p-1 shadow-xs">
          <button
            type="button"
            onClick={() => setTab("builder")}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
              tab === "builder" ? "bg-zinc-950 text-white" : "text-zinc-600 hover:text-zinc-950"
            }`}
          >
            Automation Builder
          </button>
          <button
            type="button"
            onClick={() => setTab("templates")}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
              tab === "templates" ? "bg-zinc-950 text-white" : "text-zinc-600 hover:text-zinc-950"
            }`}
          >
            Templates
          </button>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-800 shadow-xs"
          >
            {accounts.length === 0 ? (
              <option value="">No IG account</option>
            ) : (
              accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  @{a.ig_username}
                </option>
              ))
            )}
          </select>

          <button
            type="button"
            disabled={saving || !accountId}
            onClick={startAutomation}
            className="inline-flex items-center gap-2 rounded-full bg-[#c8ff00] px-5 py-2 text-xs font-bold text-zinc-950 shadow-xs transition hover:bg-[#b8f000] disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5 fill-zinc-950" />
            {saving ? "Saving..." : "Start Automation"}
          </button>
        </div>
      </div>

      {tab === "templates" ? (
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-bold text-zinc-950">Automation Templates</h2>
            <p className="text-xs text-zinc-500">Pick a template to pre-fill your automation builder.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TEMPLATES.map((tpl) => (
              <button
                key={tpl.title}
                type="button"
                onClick={() => {
                  setName(tpl.title);
                  setKeywords([tpl.keyword]);
                  setReplyText(tpl.reply);
                  setTab("builder");
                }}
                className="text-left rounded-2xl border border-zinc-200 bg-white p-4 shadow-xs transition-all hover:-translate-y-0.5 hover:border-zinc-400 hover:shadow-md space-y-3"
              >
                <span className="inline-block rounded-full bg-zinc-100 px-2.5 py-0.5 text-[10px] font-semibold text-zinc-600">
                  {tpl.category}
                </span>
                <div>
                  <div className="text-sm font-bold text-zinc-950">{tpl.title}</div>
                  <div className="mt-1 text-xs text-zinc-500">{tpl.desc}</div>
                </div>
                <div className="rounded-xl bg-zinc-50 p-2.5 space-y-1.5 border border-zinc-100">
                  <div className="rounded-lg bg-white px-2.5 py-1.5 text-[11px] text-zinc-700 border border-zinc-200/70">
                    {tpl.userMsg}
                  </div>
                  <div className="ml-4 rounded-lg bg-zinc-700 px-2.5 py-1.5 text-[11px] text-white">
                    {tpl.reply}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Dotted Canvas + iPhone DM Preview */}
          <div className="lg:col-span-6 rounded-3xl border border-zinc-200 bg-dot-grid p-6 flex flex-col items-center justify-center min-h-[500px]">
            <div className="w-full max-w-[270px] rounded-[36px] border-[6px] border-zinc-900 bg-zinc-950 p-3 text-white shadow-2xl">
              <div className="mx-auto mb-3 h-1.5 w-16 rounded-full bg-zinc-800" />
              <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2.5 px-1">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-amber-400 via-fuchsia-500 to-indigo-500" />
                  <span className="text-xs font-semibold">
                    {activeAccount ? `@${activeAccount.ig_username}` : "@your_account"}
                  </span>
                </div>
                <span className="text-[10px] text-zinc-400">DM</span>
              </div>

              <div className="my-4 space-y-3 min-h-[260px] px-1">
                <div className="flex justify-end">
                  <span className="rounded-2xl bg-indigo-600 px-3 py-1.5 text-xs font-medium uppercase">
                    {keywords[0] || "LINK"}
                  </span>
                </div>
                <div className="text-center text-[10px] text-zinc-500">9:08 AM</div>
                <div className="flex items-start gap-2">
                  <div className="h-5 w-5 shrink-0 rounded-full bg-gradient-to-tr from-amber-400 via-fuchsia-500 to-indigo-500 mt-1" />
                  <div className="rounded-2xl bg-zinc-800 px-3 py-2 text-xs text-zinc-100 leading-relaxed">
                    {replyText || "Set up a message..."}
                  </div>
                </div>
              </div>

              <div className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-2 text-[11px] text-zinc-500">
                Message...
              </div>
            </div>
            <span className="mt-4 rounded-full bg-zinc-950 px-4 py-1 text-[11px] font-semibold text-white">
              DM Preview
            </span>
          </div>

          {/* Right Configuration Panel */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                1. Trigger Keywords
              </div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Automation name"
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-medium text-zinc-950"
              />
              <div className="text-xs text-zinc-500">Suggested keywords:</div>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_KEYWORDS.map((kw) => {
                  const active = keywords.includes(kw);
                  return (
                    <button
                      key={kw}
                      type="button"
                      onClick={() => toggleKeyword(kw)}
                      className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                        active
                          ? "bg-zinc-950 text-white"
                          : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                      }`}
                    >
                      {kw}
                    </button>
                  );
                })}
              </div>
              <div className="flex gap-2 pt-1">
                <input
                  type="text"
                  value={customKw}
                  onChange={(e) => setCustomKw(e.target.value)}
                  placeholder="Add custom keyword..."
                  className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs"
                />
                <button
                  type="button"
                  onClick={addCustomKeyword}
                  className="rounded-xl border border-zinc-200 px-3 py-1.5 text-xs font-semibold hover:bg-zinc-100"
                >
                  Add
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                  2. They will get a DM with
                </div>
                <Sparkles className="h-4 w-4 text-zinc-400" />
              </div>
              <textarea
                rows={4}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="Enter your message here..."
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-950"
              />
            </div>

            <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-xs space-y-2">
              <div className="text-xs font-bold text-zinc-700">Active Rules ({rules.length})</div>
              {rules.length === 0 ? (
                <div className="text-xs text-zinc-400">No saved rules yet. Click Start Automation above!</div>
              ) : (
                rules.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between rounded-xl bg-zinc-50 px-3 py-2 text-xs"
                  >
                    <span className="font-medium text-zinc-800">{r.name}</span>
                    <button
                      type="button"
                      onClick={() => deleteRule(r.id)}
                      className="text-zinc-400 hover:text-rose-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
