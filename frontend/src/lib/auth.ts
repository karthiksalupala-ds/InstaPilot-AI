import { apiFetch } from "@/lib/api";

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface UserMe {
  id: string;
  email: string;
  full_name: string;
  workspaces: WorkspaceSummary[];
}

export function getStoredAuth(): { accessToken: string; workspaceId: string } | null {
  if (typeof window === "undefined") return null;
  const accessToken = localStorage.getItem("instapilot_access_token");
  const workspaceId = localStorage.getItem("instapilot_workspace_id");
  if (!accessToken || !workspaceId) return null;
  return { accessToken, workspaceId };
}

export async function syncWorkspaceSession(accessToken: string): Promise<UserMe> {
  const me = await apiFetch<UserMe>("/auth/me", { accessToken });
  if (me.workspaces.length > 0 && !localStorage.getItem("instapilot_workspace_id")) {
    localStorage.setItem("instapilot_workspace_id", me.workspaces[0].id);
  }
  return me;
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("instapilot_access_token");
  localStorage.removeItem("instapilot_refresh_token");
  localStorage.removeItem("instapilot_workspace_id");
}
