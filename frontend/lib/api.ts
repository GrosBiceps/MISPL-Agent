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
  conversation_id: number | null;
}

export interface ChatHistoryMessage {
  role: string;
  content: string;
}

export function askChat(
  question: string,
  labContext?: string,
  conversationHistory?: ChatHistoryMessage[],
  conversationId?: number | null
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      lab_context: labContext || undefined,
      conversation_history: conversationHistory && conversationHistory.length > 0 ? conversationHistory : undefined,
      conversation_id: conversationId ?? undefined,
    }),
  });
}

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  sources: SourceOut[] | null;
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: ConversationMessage[];
}

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/conversations");
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`);
}

export function deleteConversation(id: number): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/conversations/${id}`, { method: "DELETE" });
}

export interface UserBase {
  id: number;
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
  is_active: boolean;
}

export interface AdminUser extends UserBase {
  total_tokens_30d: number;
  last_active_at: string | null;
}

export interface CreateUserResult extends UserBase {
  temporary_password: string;
}

export interface UpdateUserPayload {
  display_name?: string;
  platform_role?: string;
  can_use_dsi_mode?: boolean;
  is_active?: boolean;
}

export interface UsageDay {
  date: string;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}

export function listAdminUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>("/admin/users");
}

export function createAdminUser(payload: {
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
}): Promise<CreateUserResult> {
  return request<CreateUserResult>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminUser(id: number, payload: UpdateUserPayload): Promise<UserBase> {
  return request<UserBase>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resetAdminPassword(id: number): Promise<{ temporary_password: string }> {
  return request<{ temporary_password: string }>(`/admin/users/${id}/reset-password`, {
    method: "POST",
  });
}

export function revokeAdminSessions(id: number): Promise<{ revoked: number }> {
  return request<{ revoked: number }>(`/admin/users/${id}/revoke-sessions`, {
    method: "POST",
  });
}

export function getUserUsageDaily(id: number, days = 30): Promise<UsageDay[]> {
  return request<UsageDay[]>(`/admin/users/${id}/usage-daily?days=${days}`);
}
