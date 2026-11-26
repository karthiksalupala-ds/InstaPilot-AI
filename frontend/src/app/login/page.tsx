"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, TokenPair } from "@/lib/api";
import { syncWorkspaceSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "bootstrap">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/bootstrap";
      const body =
        mode === "login"
          ? { email, password }
          : { email, password, full_name: fullName, workspace_name: "Private Workspace" };

      const tokens = await apiFetch<TokenPair>(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });
      localStorage.setItem("instapilot_access_token", tokens.access_token);
      localStorage.setItem("instapilot_refresh_token", tokens.refresh_token);
      await syncWorkspaceSession(tokens.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-12 max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold">
          {mode === "login" ? "Sign in to InstaPilot AI" : "Initialize Owner Account"}
        </h1>
        <p className="mt-1 text-xs text-zinc-400">
          Private mode: public sign-ups are disabled once initialized.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "bootstrap" && (
          <div>
            <label className="text-xs text-zinc-400">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
            />
          </div>
        )}

        <div>
          <label className="text-xs text-zinc-400">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="text-xs text-zinc-400">Password (min 8 chars)</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Owner & Workspace"}
        </button>
      </form>

      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "bootstrap" : "login")}
        className="w-full text-center text-xs text-zinc-400 hover:text-zinc-200"
      >
        {mode === "login"
          ? "First time setup? Initialize owner account"
          : "Already initialized? Back to sign in"}
      </button>
    </div>
  );
}
