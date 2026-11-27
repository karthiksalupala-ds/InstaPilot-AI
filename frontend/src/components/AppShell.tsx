"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  ChevronDown,
  Inbox,
  Instagram,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  Sliders,
  UserCheck,
  Users,
  Workflow,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { clearAuthSession, getStoredAuth, UserMe } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/accounts", label: "Instagram Accounts", icon: Instagram },
  { href: "/automation", label: "Automations", icon: Workflow },
  { href: "/inbox", label: "Unified Inbox", icon: Inbox },
  { href: "/agents", label: "AI Agents", icon: Bot },
  { href: "/agent-config", label: "Agent Config", icon: Sliders },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/leads", label: "Contacts & CRM", icon: UserCheck },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/logs", label: "Activity Logs", icon: Activity },
  { href: "/settings", label: "Workspace Settings", icon: Settings },
  { href: "/users", label: "User Management", icon: Users },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<UserMe | null>(null);
  const [accountCount, setAccountCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const auth = getStoredAuth();
    if (!auth) return;
    apiFetch<UserMe>("/auth/me", auth).then(setMe).catch(() => undefined);
    apiFetch<Array<{ id: string }>>("/instagram/accounts", auth)
      .then((list) => setAccountCount(list.length))
      .catch(() => undefined);
  }, [pathname]);

  function handleSignOut() {
    clearAuthSession();
    setMe(null);
    setMenuOpen(false);
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-[#f8f9fb] text-zinc-950">
      <aside className="hidden w-64 shrink-0 border-r border-zinc-200/80 bg-white lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-2.5 px-5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.jpg"
            alt="InstaPilot AI"
            className="h-8 w-8 rounded-xl object-cover shadow-sm"
          />
          <span className="text-base font-extrabold tracking-tight text-zinc-950">
            INSTAPILOT
          </span>
        </div>

        <div className="relative px-4 pb-3">
          <button
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex w-full items-center justify-between rounded-xl border border-zinc-200 bg-zinc-50/80 px-3 py-2 text-left transition hover:bg-zinc-100"
          >
            <div className="min-w-0">
              <div className="truncate text-xs font-semibold text-zinc-900">
                {me?.workspaces[0]?.name ?? "My Workspace"}
              </div>
              <div className="text-[11px] text-zinc-500">
                {me ? me.email : "Not signed in"}
              </div>
            </div>
            <ChevronDown className="h-4 w-4 shrink-0 text-zinc-400" />
          </button>

          {menuOpen && (
            <div className="absolute left-4 right-4 top-14 z-30 rounded-2xl border border-zinc-200 bg-white/95 p-2 shadow-xl backdrop-blur-md">
              <Link
                href="/settings"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-100"
              >
                <Settings className="h-3.5 w-3.5" />
                Workspace Settings
              </Link>
              {me ? (
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign Out
                </button>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-zinc-900 hover:bg-zinc-100"
                >
                  Sign In
                </Link>
              )}
            </div>
          )}
        </div>

        <div className="px-4 pb-4">
          <Link
            href="/automation"
            className="flex w-full items-center justify-center gap-2 rounded-full bg-[#c8ff00] px-4 py-2.5 text-sm font-semibold text-zinc-950 shadow-sm transition-all hover:bg-[#b8f000] hover:scale-[1.01] active:scale-[0.99]"
          >
            <Plus className="h-4 w-4 stroke-[2.5]" />
            New Automation
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium transition-all ${
                  active
                    ? "bg-zinc-100 text-zinc-950 font-semibold"
                    : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-950"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-zinc-950" : "text-zinc-400"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="m-3 rounded-2xl border border-zinc-200 bg-zinc-50/70 p-3.5 text-xs space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">IG accounts</span>
            <span className="font-semibold text-zinc-900">{accountCount}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200">
            <div
              className="h-full rounded-full bg-[#c8ff00] transition-all"
              style={{ width: accountCount > 0 ? "100%" : "12%" }}
            />
          </div>
          <div className="flex items-center justify-between pt-0.5">
            <span className="text-zinc-500">Cloud Worker</span>
            <span className="inline-flex items-center gap-1.5 font-medium text-emerald-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Online
            </span>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-16 items-center justify-between border-b border-zinc-200/80 bg-white/80 px-6 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-zinc-500">
              Instagram AI Automation Studio
            </span>
          </div>
          <div className="flex items-center gap-3">
            {!me && (
              <Link
                href="/login"
                className="rounded-full border border-zinc-200 bg-white px-4 py-1.5 text-xs font-semibold text-zinc-900 shadow-xs transition hover:bg-zinc-50"
              >
                Sign In
              </Link>
            )}
            <Link
              href="/logs"
              aria-label="Activity & Alerts"
              className="relative rounded-full border border-zinc-200 bg-white p-2 text-zinc-600 transition hover:bg-zinc-50"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </Link>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
