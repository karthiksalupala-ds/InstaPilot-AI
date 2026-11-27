"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { clearAuthSession, getStoredAuth, UserMe } from "@/lib/auth";

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
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">Workspace Settings</h1>
        <p className="text-sm text-zinc-500">
          Manage your workspace identity and active session.
        </p>
      </div>

      <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-xs space-y-4">
        <div>
          <label className="text-xs font-medium text-zinc-500">Active Workspace</label>
          <div className="mt-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-medium text-zinc-900">
            {me?.workspaces[0]?.name ?? "Not signed in"}
          </div>
        </div>
        <button
          type="button"
          onClick={signOut}
          className="rounded-full border border-rose-200 bg-rose-50 px-5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
