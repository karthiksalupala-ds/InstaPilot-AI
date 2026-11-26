"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredAuth } from "@/lib/auth";

interface MemberRow {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export default function UsersPage() {
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "operator" | "viewer">("operator");

  async function loadMembers() {
    const auth = getStoredAuth();
    if (!auth) return;
    const data = await apiFetch<MemberRow[]>(`/workspaces/${auth.workspaceId}/members`, auth);
    setMembers(data);
  }

  useEffect(() => {
    void loadMembers().catch(() => undefined);
  }, []);

  async function inviteMember(e: React.FormEvent) {
    e.preventDefault();
    const auth = getStoredAuth();
    if (!auth) return;
    await apiFetch(`/workspaces/${auth.workspaceId}/members`, {
      ...auth,
      method: "POST",
      body: JSON.stringify({ email, full_name: fullName, password, role }),
    });
    setEmail("");
    setFullName("");
    setPassword("");
    await loadMembers();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">User Management</h1>
        <p className="text-sm text-zinc-400">
          Private mode: invite-only workspace roles (owner, admin, operator, viewer).
        </p>
      </div>

      <form onSubmit={inviteMember} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 grid gap-3 sm:grid-cols-4">
        <input
          type="text"
          required
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Temp password (8+)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as "admin" | "operator" | "viewer")}
          className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
        >
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="viewer">Viewer</option>
        </select>
        <button
          type="submit"
          className="sm:col-span-4 w-fit rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          + Invite Member
        </button>
      </form>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-800 bg-zinc-950/60 text-xs uppercase text-zinc-400">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Role</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/80">
            {members.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-4 text-xs text-zinc-400">
                  Sign in to view workspace members.
                </td>
              </tr>
            ) : (
              members.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3 font-medium">{m.full_name}</td>
                  <td className="px-4 py-3 text-zinc-400">{m.email}</td>
                  <td className="px-4 py-3 uppercase text-xs text-indigo-300">{m.role}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
