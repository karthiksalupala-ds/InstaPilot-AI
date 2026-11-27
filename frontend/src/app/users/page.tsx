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
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">User Management</h1>
        <p className="text-sm text-zinc-500">
          Private mode: invite-only workspace roles (owner, admin, operator, viewer).
        </p>
      </div>

      <form onSubmit={inviteMember} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-xs grid gap-3 sm:grid-cols-4">
        <input
          type="text"
          required
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
        />
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Temp password (8+)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as "admin" | "operator" | "viewer")}
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
        >
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="viewer">Viewer</option>
        </select>
        <button
          type="submit"
          className="sm:col-span-4 w-fit rounded-full bg-[#c8ff00] px-5 py-2 text-xs font-bold text-zinc-950 hover:bg-[#b8f000]"
        >
          + Invite Member
        </button>
      </form>

      <div className="rounded-2xl border border-zinc-200 bg-white shadow-xs overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-zinc-50 text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Role</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {members.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-4 text-xs text-zinc-500">
                  Sign in to view workspace members.
                </td>
              </tr>
            ) : (
              members.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3 font-medium text-zinc-900">{m.full_name}</td>
                  <td className="px-4 py-3 text-zinc-500">{m.email}</td>
                  <td className="px-4 py-3 uppercase text-xs font-semibold text-zinc-700">{m.role}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
