"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface IgAccount {
  id: string;
  ig_username: string;
}

interface KbDoc {
  id: string;
  title: string;
  source_type: string;
  status: string;
}

export default function KnowledgePage() {
  const [accounts, setAccounts] = useState<IgAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [docs, setDocs] = useState<KbDoc[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<"faq" | "policy" | "manual_text">("faq");

  async function loadDocs(accId: string) {
    const auth = getStoredAuth();
    if (!auth || !accId) return;
    const list = await apiFetch<KbDoc[]>(`/accounts/${accId}/knowledge/documents`, auth);
    setDocs(list);
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
    if (accountId) void loadDocs(accountId);
  }, [accountId]);

  async function addDocument(e: React.FormEvent) {
    e.preventDefault();
    const auth = getStoredAuth();
    if (!auth || !accountId) return;
    await apiFetch(`/accounts/${accountId}/knowledge/documents`, {
      ...auth,
      method: "POST",
      body: JSON.stringify({
        source_type: sourceType,
        title,
        raw_content: content,
      }),
    });
    setTitle("");
    setContent("");
    await loadDocs(accountId);
  }

  async function deleteDoc(docId: string) {
    const auth = getStoredAuth();
    if (!auth || !accountId) return;
    await apiFetch(`/accounts/${accountId}/knowledge/documents/${docId}`, {
      ...auth,
      method: "DELETE",
    });
    await loadDocs(accountId);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge Base (Account-Isolated RAG)</h1>
          <p className="text-sm text-zinc-400">
            Manage FAQs, policies, and documents per Instagram account.
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

      <form onSubmit={addDocument} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <input
            type="text"
            required
            placeholder="Title (e.g. Shipping Policy)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="sm:col-span-2 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
          />
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as "faq" | "policy" | "manual_text")}
            className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
          >
            <option value="faq">FAQ</option>
            <option value="policy">Policy</option>
            <option value="manual_text">Manual Text</option>
          </select>
        </div>
        <textarea
          required
          rows={3}
          placeholder="Paste knowledge content..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm"
        />
        <button
          type="submit"
          disabled={!accountId}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          + Add & Index Document
        </button>
      </form>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-950/60 text-xs uppercase text-zinc-400">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Source Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/80">
            {docs.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-xs text-zinc-400">
                  No knowledge documents yet.
                </td>
              </tr>
            ) : (
              docs.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 font-medium">{d.title}</td>
                  <td className="px-4 py-3 uppercase text-xs text-zinc-300">{d.source_type}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs text-emerald-300">
                      {d.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => deleteDoc(d.id)}
                      className="text-xs text-rose-400 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
