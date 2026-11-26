"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface LeadRow {
  id: string;
  customer_id: string;
  interest_category: string | null;
  status: string;
  notes: string | null;
  follow_up_at: string | null;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadRow[]>([]);

  async function loadLeads() {
    const auth = getStoredAuth();
    if (!auth) return;
    const data = await apiFetch<LeadRow[]>("/leads", auth);
    setLeads(data);
  }

  useEffect(() => {
    void loadLeads().catch(() => undefined);
  }, []);

  async function updateStatus(leadId: string, status: string) {
    const auth = getStoredAuth();
    if (!auth) return;
    await apiFetch(`/leads/${leadId}`, {
      ...auth,
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await loadLeads();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Leads & CRM</h1>
        <p className="text-sm text-zinc-400">
          Track AI-captured and operator-managed leads across all connected Instagram accounts.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-950/60 text-xs uppercase text-zinc-400">
            <tr>
              <th className="px-4 py-3">Customer ID</th>
              <th className="px-4 py-3">Interest</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/80">
            {leads.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-4 text-xs text-zinc-400">
                  No leads captured yet.
                </td>
              </tr>
            ) : (
              leads.map((l) => (
                <tr key={l.id}>
                  <td className="px-4 py-3 font-mono text-xs">{l.customer_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">{l.interest_category ?? "—"}</td>
                  <td className="px-4 py-3">
                    <select
                      value={l.status}
                      onChange={(e) => updateStatus(l.id, e.target.value)}
                      className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs uppercase"
                    >
                      <option value="new">New</option>
                      <option value="qualified">Qualified</option>
                      <option value="contacted">Contacted</option>
                      <option value="converted">Converted</option>
                      <option value="lost">Lost</option>
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400">{l.notes ?? "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
