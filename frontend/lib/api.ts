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
  retrieved: { source: string | null; scope?: string; similarity: number }[];
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
  project_id: string | null;
}
export const sendMessage = (
  message: string,
  conversation_id?: string | null,
  files?: File[],
  project_id?: string | null,
) => {
  const fd = new FormData();
  fd.append("message", message);
  if (conversation_id) fd.append("conversation_id", conversation_id);
  if (project_id) fd.append("project_id", project_id);
  (files || []).forEach((f) => fd.append("files", f));
  return req<ChatReply>("/chat", { method: "POST", body: fd });
};

// Streaming chat (SSE over fetch). Resolves when the stream ends; rejects on
// HTTP errors or an in-stream {"type":"error"} event.
export interface StreamCallbacks {
  onMeta?: (meta: {
    conversation_id: string;
    title: string;
    retrieved: ChatReply["retrieved"];
    skill?: { name: string; command: string } | null;
  }) => void;
  onDelta?: (text: string) => void;
  onTag?: (tag: ChatReply["tag"]) => void;
}
export async function sendMessageStream(
  message: string,
  conversation_id: string | null | undefined,
  files: File[] | undefined,
  project_id: string | null | undefined,
  cb: StreamCallbacks,
): Promise<void> {
  const fd = new FormData();
  fd.append("message", message);
  if (conversation_id) fd.append("conversation_id", conversation_id);
  if (project_id) fd.append("project_id", project_id);
  (files || []).forEach((f) => fd.append("files", f));

  const token = getToken();
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  if (!res.ok || !res.body) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const block of events) {
      const line = block.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      let event: any;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue;
      }
      if (event.type === "meta") cb.onMeta?.(event);
      else if (event.type === "delta") cb.onDelta?.(event.text);
      else if (event.type === "tag") cb.onTag?.(event.tag);
      else if (event.type === "error") throw new Error(event.detail || "Stream failed");
    }
  }
}

// --- projects (personal + team) ---
export interface Project {
  id: string;
  name: string;
  kind: "user" | "team";
  n_docs: number;
  can_edit: boolean;
}
export const listProjects = () => req<Project[]>("/projects");
export const createProject = (name: string) =>
  req<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) });
export const deleteProject = (id: string) => req<any>(`/projects/${id}`, { method: "DELETE" });
export const listProjectDocs = (id: string) => req<KDoc[]>(`/projects/${id}/knowledge`);
export const uploadProjectDocs = (id: string, files: FileList | File[]) =>
  uploadTo(`/projects/${id}/knowledge/upload`, files);
export const deleteProjectDoc = (id: string, docId: string) =>
  req<any>(`/projects/${id}/knowledge/${docId}`, { method: "DELETE" });

// --- knowledge folders (team, manager-curated) ---
export interface Folder {
  id: string;
  name: string;
  n_docs: number;
  n_granted: number | null;
  n_requests: number | null;
  my_status: string | null; // 'granted' | 'requested' | null
  can_edit: boolean;
}
export const listFolders = () => req<Folder[]>("/folders");
export const createFolder = (name: string) =>
  req<Folder>("/folders", { method: "POST", body: JSON.stringify({ name }) });
export const deleteFolder = (id: string) => req<any>(`/folders/${id}`, { method: "DELETE" });
export const listFolderDocs = (id: string) => req<KDoc[]>(`/folders/${id}/knowledge`);
export const uploadFolderDocs = (id: string, files: FileList | File[]) =>
  uploadTo(`/folders/${id}/knowledge/upload`, files);
export const deleteFolderDoc = (id: string, docId: string) =>
  req<any>(`/folders/${id}/knowledge/${docId}`, { method: "DELETE" });
export const folderAccess = (id: string) =>
  req<{ id: string; name: string; status: string }[]>(`/folders/${id}/access`);
export const folderAccessChange = (id: string, user_id: string, action: "grant" | "revoke") =>
  req<any>(`/folders/${id}/access`, { method: "POST", body: JSON.stringify({ user_id, action }) });
export const requestFolderAccess = (id: string) =>
  req<any>(`/folders/${id}/request`, { method: "POST" });

// --- a project's imported folders ---
export interface ProjectFolders {
  imported: { id: string; name: string; n_docs: number }[];
  available: { id: string; name: string; n_docs: number }[];
}
export const getProjectFolders = (pid: string) => req<ProjectFolders>(`/projects/${pid}/folders`);
export const importFolder = (pid: string, fid: string) =>
  req<any>(`/projects/${pid}/folders/${fid}`, { method: "POST" });
export const unimportFolder = (pid: string, fid: string) =>
  req<any>(`/projects/${pid}/folders/${fid}`, { method: "DELETE" });
export const listConversations = (q?: string) =>
  req<Conversation[]>(`/conversations${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const getConversation = (id: string) =>
  req<{
    id: string;
    skill: { name: string; command: string } | null;
    messages: { role: string; content: string }[];
  }>(`/conversations/${id}`);
export const deleteConversation = (id: string) =>
  req<any>(`/conversations/${id}`, { method: "DELETE" });

// --- scoped knowledge (org users): personal / team / member ---
function uploadTo(path: string, files: FileList | File[]) {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  return req<{ results: any[] }>(path, { method: "POST", body: fd });
}
export const getMyDocs = () => req<KDoc[]>("/knowledge/me");
export const uploadMyDocs = (files: FileList | File[]) => uploadTo("/knowledge/me/upload", files);
export const deleteMyDoc = (id: string) => req<any>(`/knowledge/me/${id}`, { method: "DELETE" });

export const getTeamDocs = () => req<KDoc[]>("/knowledge/team");
export const uploadTeamDocs = (files: FileList | File[]) => uploadTo("/knowledge/team/upload", files);
export const deleteTeamDoc = (id: string) => req<any>(`/knowledge/team/${id}`, { method: "DELETE" });

export const getMemberDocs = (uid: string) => req<KDoc[]>(`/knowledge/member/${uid}`);
export const uploadMemberDocs = (uid: string, files: FileList | File[]) =>
  uploadTo(`/knowledge/member/${uid}/upload`, files);
export const deleteMemberDoc = (uid: string, id: string) =>
  req<any>(`/knowledge/member/${uid}/${id}`, { method: "DELETE" });

// --- dashboards (org users) ---
export const dashMe = () => req<any>("/dashboard/me");
export const dashTeam = () => req<any>("/dashboard/team");
export const dashMember = (id: string) => req<any>(`/dashboard/member/${id}`);

// --- knowledge templates (admin) ---
export interface KTemplate {
  id: string;
  kind: "stage" | "sector";
  key: string;
  name: string;
  description: string;
  n_docs: number;
  n_chunks: number;
}
export const listTemplates = () => req<KTemplate[]>("/templates");
export const createSector = (key: string, name: string, description = "") =>
  req<any>("/templates/sectors", { method: "POST", body: JSON.stringify({ key, name, description }) });
export const listTemplateDocs = (tid: string) => req<KDoc[]>(`/templates/${tid}/knowledge`);
export const uploadTemplateDocs = (tid: string, files: FileList | File[]) =>
  uploadTo(`/templates/${tid}/knowledge/upload`, files);
export const deleteTemplateDoc = (tid: string, docId: string) =>
  req<any>(`/templates/${tid}/knowledge/${docId}`, { method: "DELETE" });
export const applyTemplate = (tid: string, orgId: string) =>
  req<{ template: string; copied: string[]; skipped: string[] }>(`/templates/${tid}/apply/${orgId}`, { method: "POST" });

// --- skills ---
export interface Skill {
  id: string;
  name: string;
  command: string;
  description: string;
  body: string;
  n_orgs?: number;
}
export const listSkills = () => req<Skill[]>("/skills");
export const createSkill = (s: { name: string; command: string; description: string; body: string }) =>
  req<Skill>("/skills", { method: "POST", body: JSON.stringify(s) });
export const updateSkill = (id: string, s: Partial<Skill>) =>
  req<Skill>(`/skills/${id}`, { method: "PATCH", body: JSON.stringify(s) });
export const deleteSkill = (id: string) => req<any>(`/skills/${id}`, { method: "DELETE" });
export const orgSkillGrants = (orgId: string) =>
  req<{ id: string; name: string; command: string; description: string; granted: boolean }[]>(`/skills/grants/${orgId}`);
export const grantSkill = (orgId: string, skillId: string) =>
  req<any>(`/skills/grants/${orgId}/${skillId}`, { method: "POST" });
export const revokeSkill = (orgId: string, skillId: string) =>
  req<any>(`/skills/grants/${orgId}/${skillId}`, { method: "DELETE" });
export const mySkills = () =>
  req<{ id: string; name: string; command: string; description: string }[]>("/skills/mine");

export { API_BASE };
