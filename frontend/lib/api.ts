const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // pas de corps JSON exploitable
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export interface MeResponse {
  id: number;
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
}

export function login(email: string, password: string): Promise<MeResponse> {
  return request<MeResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<{ detail: string }> {
  return request("/auth/logout", { method: "POST" });
}

export function getMe(): Promise<MeResponse> {
  return request<MeResponse>("/auth/me");
}

export interface SourceOut {
  function_name: string;
  source: string;
  score: number;
  exact_match: boolean;
}

export interface ChatResponse {
  response: string | null;
  sources: SourceOut[];
  blocked: boolean;
  dlp_alerts: string[];
}

export interface ChatHistoryMessage {
  role: string;
  content: string;
}

export function askChat(
  question: string,
  labContext?: string,
  conversationHistory?: ChatHistoryMessage[]
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      lab_context: labContext || undefined,
      conversation_history: conversationHistory && conversationHistory.length > 0 ? conversationHistory : undefined,
    }),
  });
}
