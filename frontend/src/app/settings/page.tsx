"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { clearAuthSession, getStoredAuth, UserMe } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<UserMe | null>(null);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<UserMe>("/auth/me", auth).then(setMe).catch(() => undefined);
  }, []);

  function signOut() {
    clearAuthSession();
    router.push("/login");
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Workspace Settings</h1>
        <p className="text-sm text-zinc-400">
          Manage workspace identity, LLM defaults, and session status.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 space-y-4">
        <div>
          <label className="text-xs text-zinc-400">Active Workspace</label>
          <div className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
            {me?.workspaces[0]?.name ?? "Not signed in"}
          </div>
        </div>
        <div>
          <label className="text-xs text-zinc-400">LLM Key Source</label>
          <div className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300">
            Global Backend <code>.env</code> (GEMINI_API_KEY / GROQ_API_KEY)
          </div>
        </div>
        <button
          type="button"
          onClick={signOut}
          className="rounded-lg border border-rose-500/40 px-4 py-2 text-sm font-medium text-rose-300 hover:bg-rose-500/10"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
