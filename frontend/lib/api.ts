const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const TOKEN_KEY = "pulse_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: "kpmg_admin" | "manager" | "employee";
  org_id: string | null;
  team_id: string | null;
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init.body && !(init.body instanceof FormData))
    headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

// --- auth ---
export async function login(email: string, password: string) {
  const data = await req<{ token: string; user: AuthUser }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  return data.user;
}
export const me = () => req<AuthUser>("/auth/me");

// --- orgs (admin) ---
export interface Org {
  id: string;
  name: string;
  maturity_stage: number;
  maturity_label: string;
  description: string;
  coach_prompt: string;
  settings: Record<string, boolean>;
  n_users?: number;
  n_chunks?: number;
}
export const listOrgs = () => req<Org[]>("/orgs");
export const getOrg = (id: string) => req<Org>(`/orgs/${id}`);
export const createOrg = (body: Partial<Org>) =>
  req<Org>("/orgs", { method: "POST", body: JSON.stringify(body) });
export const updateOrg = (id: string, body: Partial<Org>) =>
  req<Org>(`/orgs/${id}`, { method: "PATCH", body: JSON.stringify(body) });

// --- users / teams (admin) ---
export interface OrgUser {
  id: string;
  name: string;
  email: string;
  role: string;
  team_id: string | null;
  team_name: string | null;
}
export interface Team {
  id: string;
  name: string;
  manager_user_id: string | null;
}
export const listUsers = (orgId: string) =>
  req<OrgUser[]>(`/orgs/${orgId}/users`);
export const createUser = (orgId: string, body: any) =>
  req<any>(`/orgs/${orgId}/users`, { method: "POST", body: JSON.stringify(body) });
export const listTeams = (orgId: string) => req<Team[]>(`/orgs/${orgId}/teams`);
export const createTeam = (orgId: string, body: any) =>
  req<any>(`/orgs/${orgId}/teams`, { method: "POST", body: JSON.stringify(body) });

// --- knowledge (admin) ---
export interface KDoc {
  id: string;
  filename: string;
  status: string;
  n_chunks: number;
  error: string | null;
  created_at: string;
}
export const listDocs = (orgId: string) =>
  req<KDoc[]>(`/orgs/${orgId}/knowledge`);
export const deleteDoc = (orgId: string, docId: string) =>
  req<any>(`/orgs/${orgId}/knowledge/${docId}`, { method: "DELETE" });
export async function uploadDocs(orgId: string, files: FileList) {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  return req<{ results: any[] }>(`/orgs/${orgId}/knowledge/upload`, {
    method: "POST",
    body: fd,
  });
}

// --- coach / chatbot (org users) ---
export interface ChatReply {
  reply: string;
  conversation_id: string;
  title: string;
  retrieved: { source: string | null; similarity: number }[];
  tag: {
    pillar: string | null;
    phase: string;
    usage_type: string;
    evidence_backed: boolean;
    quality_score: number;
    handoff: boolean;
    fired_signals?: {
      id: string;
      pillar: string;
      polarity: number;
      text: string;
      evidence?: string;
    }[];
  } | null;
}
export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}
export const sendMessage = (
  message: string,
  conversation_id?: string | null,
  files?: File[],
) => {
  const fd = new FormData();
  fd.append("message", message);
  if (conversation_id) fd.append("conversation_id", conversation_id);
  (files || []).forEach((f) => fd.append("files", f));
  return req<ChatReply>("/chat", { method: "POST", body: fd });
};
export const listConversations = (q?: string) =>
  req<Conversation[]>(`/conversations${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const getConversation = (id: string) =>
  req<{ id: string; messages: { role: string; content: string }[] }>(`/conversations/${id}`);
export const deleteConversation = (id: string) =>
  req<any>(`/conversations/${id}`, { method: "DELETE" });

// --- dashboards (org users) ---
export const dashMe = () => req<any>("/dashboard/me");
export const dashTeam = () => req<any>("/dashboard/team");
export const dashMember = (id: string) => req<any>(`/dashboard/member/${id}`);

export { API_BASE };
