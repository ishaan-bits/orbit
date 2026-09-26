/**
 * API origin. Default ("" = same origin) routes requests through the
 * `/api/*` rewrite in `next.config.ts`, so cookies stay first-party in
 * every environment. Set `NEXT_PUBLIC_API_URL` (e.g. the direct Render
 * URL) to bypass the proxy instead.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface Folder {
  id: string;
  name: string;
  document_count: number;
  created_at: string;
}

export type DocumentStatus = "uploaded" | "processing" | "indexed" | "failed";

export interface DocumentMeta {
  id: string;
  original_filename: string;
  file_extension: string;
  mime_type: string;
  file_size: number;
  folder_id: string | null;
  folder_name: string | null;
  status: DocumentStatus;
  chunk_count: number;
  index_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  items: DocumentMeta[];
  total: number;
}

export interface DeleteResult {
  id: string;
  status: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      credentials: "include",
      ...init,
    });
  } catch {
    throw new ApiError("Could not reach the Orbit API", 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // keep the default message
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface ListDocumentsParams {
  folderId?: string | null;
  q?: string;
}

export type UserRole = "Admin" | "HR" | "Engineering";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface RegisterInput {
  email: string;
  password: string;
  full_name?: string;
  role?: Exclude<UserRole, "Admin">;
}

export const api = {
  listFolders(): Promise<Folder[]> {
    return request<Folder[]>("/api/folders");
  },

  createFolder(name: string): Promise<Folder> {
    return request<Folder>("/api/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  },

  listDocuments(params: ListDocumentsParams = {}): Promise<DocumentList> {
    const search = new URLSearchParams();
    if (params.folderId) search.set("folder_id", params.folderId);
    if (params.q) search.set("q", params.q);
    const qs = search.toString();
    return request<DocumentList>(`/api/documents${qs ? `?${qs}` : ""}`);
  },

  uploadDocument(file: File, folderId?: string | null): Promise<DocumentMeta> {
    const form = new FormData();
    form.append("file", file);
    if (folderId) form.append("folder_id", folderId);
    return request<DocumentMeta>("/api/documents/upload", {
      method: "POST",
      body: form,
    });
  },

  deleteDocument(id: string): Promise<DeleteResult> {
    return request<DeleteResult>(`/api/documents/${id}`, {
      method: "DELETE",
    });
  },

  chatHistory(): Promise<ChatHistoryResponse> {
    return request<ChatHistoryResponse>("/api/chat/history");
  },

  register(input: RegisterInput): Promise<User> {
    return request<User>("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  },

  login(email: string, password: string): Promise<User> {
    return request<User>("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  },

  logout(): Promise<void> {
    return request<void>("/api/auth/logout", { method: "POST" });
  },

  me(): Promise<User> {
    return request<User>("/api/auth/me");
  },

  analyticsOverview(): Promise<AnalyticsOverview> {
    return request<AnalyticsOverview>("/api/analytics/overview");
  },

  analyticsDaily(days = 14): Promise<AnalyticsDaily> {
    return request<AnalyticsDaily>(`/api/analytics/daily?days=${days}`);
  },

  analyticsTopDocuments(): Promise<AnalyticsTopDocuments> {
    return request<AnalyticsTopDocuments>("/api/analytics/top-documents");
  },

  analyticsTopQueries(): Promise<AnalyticsTopQueries> {
    return request<AnalyticsTopQueries>("/api/analytics/top-queries");
  },

  analyticsRecent(): Promise<AnalyticsRecent> {
    return request<AnalyticsRecent>("/api/analytics/recent");
  },
};

export interface AnalyticsOverview {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  success_rate: number;
  avg_latency_ms: number;
  retrieved_documents_total: number;
  unique_users: number;
}

export interface AnalyticsDailyPoint {
  date: string;
  queries: number;
  successful: number;
  failed: number;
  avg_latency_ms: number;
}

export interface AnalyticsDaily {
  days: AnalyticsDailyPoint[];
}

export interface AnalyticsTopDocuments {
  documents: { document: string; count: number }[];
}

export interface AnalyticsTopQueries {
  queries: { query: string; count: number }[];
}

export interface AnalyticsRecentSearch {
  id: string;
  query: string;
  success: boolean;
  latency_ms: number;
  retrieved_documents: number;
  created_at: string;
}

export interface AnalyticsRecent {
  searches: AnalyticsRecentSearch[];
}

export interface ChatSource {
  document: string;
  page: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[] | null;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface ChatQueryResponse {
  answer: string;
  sources: ChatSource[];
  conversation_id: string;
}

export interface ChatHistoryResponse {
  conversations: ChatConversation[];
}

export interface StreamChatHandlers {
  onSources?: (sources: ChatSource[], conversationId: string) => void;
  onToken?: (text: string) => void;
  onDone?: (result: ChatQueryResponse) => void;
  onError?: (message: string) => void;
}

interface StreamEventPayload {
  text?: string;
  sources?: ChatSource[];
  conversation_id?: string;
  answer?: string;
  error?: string;
}

export async function streamChat(
  query: string,
  conversationId: string | null,
  handlers: StreamChatHandlers,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      credentials: "include",
      body: JSON.stringify({
        query,
        ...(conversationId ? { conversation_id: conversationId } : {}),
      }),
    });
  } catch {
    handlers.onError?.("Could not reach the Orbit API");
    return;
  }

  if (!response.ok || !response.body) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // keep the default message
    }
    handlers.onError?.(detail);
    return;
  }

  const dispatch = (rawBlock: string) => {
    let event = "message";
    let data = "";
    for (const line of rawBlock.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        data += line.slice(5).trim();
      }
    }
    if (!data) return;
    let payload: StreamEventPayload;
    try {
      payload = JSON.parse(data) as StreamEventPayload;
    } catch {
      return;
    }
    switch (event) {
      case "sources":
        handlers.onSources?.(payload.sources ?? [], payload.conversation_id ?? "");
        break;
      case "token":
        handlers.onToken?.(payload.text ?? "");
        break;
      case "done":
        handlers.onDone?.({
          answer: payload.answer ?? "",
          sources: payload.sources ?? [],
          conversation_id: payload.conversation_id ?? "",
        });
        break;
      case "error":
        handlers.onError?.(payload.error ?? "Answer generation failed");
        break;
    }
  };

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        dispatch(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
    }
    if (buffer.trim()) dispatch(buffer);
  } catch {
    handlers.onError?.("Connection lost while streaming the answer");
  }
}
