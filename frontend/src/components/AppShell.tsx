"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  Inbox,
  Instagram,
  LayoutDashboard,
  Settings,
  Sliders,
  Users,
  UserCheck,
  Workflow,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/accounts", label: "Instagram Accounts", icon: Instagram },
  { href: "/agents", label: "AI Agents", icon: Bot },
  { href: "/agent-config", label: "Agent Config", icon: Sliders },
  { href: "/inbox", label: "Unified Inbox", icon: Inbox, badge: "3" },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/automation", label: "Automation Rules", icon: Workflow },
  { href: "/leads", label: "Leads & CRM", icon: UserCheck },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/logs", label: "Activity Logs", icon: Activity },
  { href: "/settings", label: "Workspace Settings", icon: Settings },
  { href: "/users", label: "User Management", icon: Users },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="hidden w-64 shrink-0 border-r border-zinc-800/80 bg-zinc-900/60 lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-2.5 border-b border-zinc-800/80 px-5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.jpg"
            alt="InstaPilot AI"
            className="h-8 w-8 rounded-lg object-cover"
          />
          <div>
            <div className="text-sm font-semibold tracking-tight">InstaPilot AI</div>
            <div className="text-[11px] text-zinc-400">Private Workspace</div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                    : "text-zinc-400 hover:bg-zinc-800/70 hover:text-zinc-100"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>
                {item.badge && (
                  <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[11px] text-indigo-300">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-zinc-800/80 p-4 text-xs text-zinc-400">
          <div className="flex items-center justify-between">
            <span>Background Worker</span>
            <span className="inline-flex items-center gap-1.5 text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Ready (Phase 1)
            </span>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-16 items-center justify-between border-b border-zinc-800/80 bg-zinc-950/80 px-6 backdrop-blur">
          <div className="text-sm text-zinc-400">
            Multi-Account Instagram AI Control Center
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline-flex items-center rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs text-zinc-300">
              LLM: Gemini / Groq
            </span>
            <Link
              href="/login"
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
            >
              Sign In
            </Link>
            <button
              type="button"
              aria-label="Notifications"
              className="relative rounded-lg border border-zinc-800 bg-zinc-900 p-2 text-zinc-300 hover:bg-zinc-800"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-fuchsia-500" />
            </button>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
