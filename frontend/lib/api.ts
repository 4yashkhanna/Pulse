const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface RetrievedChunk {
  framework: string | null;
  pillar: string | null;
  phase: string | null;
  similarity: number;
}

export interface Tag {
  pillar: string;
  phase: string;
  usage_type: string;
  evidence_backed: boolean;
  quality_score: number;
  handoff: boolean;
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
  retrieved: RetrievedChunk[];
  tag: Tag | null;
}

export interface User {
  id: string;
  name: string;
  dept: string;
  role: string;
  sector: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export async function sendChat(body: {
  message: string;
  user_id: string;
  sector?: string | null;
  conversation_id?: string | null;
  history: { role: string; content: string }[];
}): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`chat failed: ${res.status}`);
  return res.json();
}

export const getUsers = () => get<User[]>("/dashboard/users");
export const getDepts = () => get<string[]>("/dashboard/depts");
export const getEmployee = (id: string) => get<any>(`/dashboard/employee/${id}`);
export const getManager = (dept: string) =>
  get<any>(`/dashboard/manager/${encodeURIComponent(dept)}`);
export const getLeadership = () => get<any>("/dashboard/leadership");
