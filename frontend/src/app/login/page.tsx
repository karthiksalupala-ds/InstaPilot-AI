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
    <div className="mx-auto mt-12 max-w-md rounded-3xl border border-zinc-200 bg-white p-7 shadow-sm space-y-5">
      <div>
        <h1 className="text-xl font-bold text-zinc-950">
          {mode === "login" ? "Sign in to InstaPilot AI" : "Initialize Owner Account"}
        </h1>
        <p className="mt-1 text-xs text-zinc-500">
          Private mode: public sign-ups are disabled once initialized.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "bootstrap" && (
          <div>
            <label className="text-xs font-medium text-zinc-600">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-950 focus:border-zinc-950 focus:outline-none"
            />
          </div>
        )}

        <div>
          <label className="text-xs font-medium text-zinc-600">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-950 focus:border-zinc-950 focus:outline-none"
          />
        </div>

        <div>
          <label className="text-xs font-medium text-zinc-600">Password (min 8 chars)</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-950 focus:border-zinc-950 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-full bg-[#c8ff00] py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-[#b8f000] disabled:opacity-50"
        >
          {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Owner & Workspace"}
        </button>
      </form>

      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "bootstrap" : "login")}
        className="w-full text-center text-xs font-medium text-zinc-500 hover:text-zinc-950"
      >
        {mode === "login"
          ? "First time setup? Initialize owner account"
          : "Already initialized? Back to sign in"}
      </button>
    </div>
  );
}
