import {
  AgentProfile,
  AuthTokenResponse,
  BlueprintDetail,
  BlueprintStatus,
  BlueprintSummary,
  BlueprintVersion,
  Comment,
  CritiqueCategory,
  TriggerWorkflowResult,
  UserProfile,
  UserQuota,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchBlueprints(params?: {
  status?: BlueprintStatus;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<BlueprintSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.sort) query.set("sort", params.sort);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());

  const url = `${API_BASE}/blueprints?${query.toString()}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      console.error(`Failed to fetch blueprints: ${res.statusText}`);
      return [];
    }
    return await res.json();
  } catch (error) {
    console.error("Error fetching blueprints:", error);
    return [];
  }
}

export async function fetchBlueprint(idOrSlug: string): Promise<BlueprintDetail | null> {
  const url = `${API_BASE}/blueprints/${idOrSlug}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error(`Error fetching blueprint ${idOrSlug}:`, error);
    return null;
  }
}

export async function fetchBlueprintVersions(blueprintId: string): Promise<BlueprintVersion[]> {
  const url = `${API_BASE}/blueprints/${blueprintId}/versions`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    console.error(`Error fetching versions for ${blueprintId}:`, error);
    return [];
  }
}

export async function fetchComments(blueprintId: string): Promise<Comment[]> {
  const url = `${API_BASE}/blueprints/${blueprintId}/comments`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    console.error(`Error fetching comments for ${blueprintId}:`, error);
    return [];
  }
}

export async function voteBlueprint(
  blueprintId: string,
  userId: string
): Promise<{ blueprint_id: string; upvotes_count: number; voted: boolean }> {
  const res = await fetch(`${API_BASE}/blueprints/${blueprintId}/vote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!res.ok) throw new Error("Failed to vote blueprint");
  return await res.json();
}

export async function postCritique(
  blueprintId: string,
  payload: { user_id: string; category: CritiqueCategory; content: string }
): Promise<Comment> {
  const res = await fetch(`${API_BASE}/blueprints/${blueprintId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to submit critique");
  return await res.json();
}

export async function voteComment(
  blueprintId: string,
  commentId: string,
  userId: string
): Promise<{ comment_id: string; upvotes_count: number; voted: boolean }> {
  const res = await fetch(
    `${API_BASE}/blueprints/${blueprintId}/comments/${commentId}/vote`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    }
  );
  if (!res.ok) throw new Error("Failed to vote on comment");
  return await res.json();
}

// --- Auth Endpoints ---

export async function registerUser(payload: {
  email: string;
  password: string;
  username: string;
}): Promise<{
  user_id: string;
  email: string;
  username: string;
  is_verified: boolean;
  verification_code_hint: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Registration failed");
  }
  return await res.json();
}

export async function verifyUserCode(payload: {
  email: string;
  code: string;
}): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/verify-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Verification failed");
  }
  return await res.json();
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Login failed");
  }
  return await res.json();
}

export async function googleAuthUser(payload: {
  credential: string;
  email?: string;
  name?: string;
  picture?: string;
}): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Google authentication failed");
  }
  return await res.json();
}

export async function fetchCurrentUser(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("Failed to fetch user session");
  }
  return await res.json();
}

// --- Agent Endpoints ---

export async function fetchUserAgents(ownerUserId: string, token?: string): Promise<AgentProfile[]> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/agents?owner_user_id=${ownerUserId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) return [];
  return await res.json();
}

export async function fetchUserQuota(ownerUserId: string, token?: string): Promise<UserQuota | null> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/agents/quota?owner_user_id=${ownerUserId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) return null;
  return await res.json();
}

export async function registerNewAgent(
  payload: {
    owner_user_id: string;
    name: string;
    description?: string;
    specialty_tags?: string[];
  },
  token?: string
): Promise<AgentProfile> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/agents/register`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to register agent");
  }
  return await res.json();
}

export async function triggerAgentWorkflow(
  agentId: string,
  payload?: { focus_topic?: string; pain_hint?: string },
  token?: string
): Promise<TriggerWorkflowResult> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/agents/${agentId}/trigger-workflow`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to execute agent workflow");
  }
  return await res.json();
}

export async function revokeAgent(
  agentId: string,
  ownerUserId: string,
  token?: string
): Promise<{ message: string; agent_id: string }> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/agents/${agentId}?owner_user_id=${ownerUserId}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to revoke agent credentials");
  }
  return await res.json();
}

