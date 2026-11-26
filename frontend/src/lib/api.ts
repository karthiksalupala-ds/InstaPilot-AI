const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { workspaceId?: string; accessToken?: string } = {}
): Promise<T> {
  const { workspaceId, accessToken, headers, ...rest } = options;
  const mergedHeaders = new Headers(headers);
  mergedHeaders.set("Content-Type", "application/json");
  if (accessToken) {
    mergedHeaders.set("Authorization", `Bearer ${accessToken}`);
  }
  if (workspaceId) {
    mergedHeaders.set("X-Workspace-Id", workspaceId);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: mergedHeaders,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || "API request failed");
  }
  return (await response.json()) as T;
}
