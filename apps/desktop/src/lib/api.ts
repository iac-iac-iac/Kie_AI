import { getSidecarUrl } from "./sidecar";
import { consumeSseStream, type StreamHandler } from "./sse";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await getSidecarUrl();
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export interface AppSettings {
  theme: "dark" | "light" | "system";
  locale: "ru" | "en";
  notifications_enabled: boolean;
  proxy: {
    enabled: boolean;
    url: string | null;
  };
  session_limit_enabled: boolean;
  session_limit_credits: number | null;
}

export interface CreditsResponse {
  credits: number;
}

export interface SessionUsageResponse {
  spent: number;
  limit: number | null;
  remaining: number | null;
}

export interface HealthResponse {
  status: string;
  has_api_key: boolean;
  version?: string;
  pricing_updated_at?: string | null;
}

export interface SystemPathsResponse {
  data_dir: string;
  db_path: string;
  media_dir: string;
  images_dir: string;
  videos_dir: string;
  logs_dir: string;
}

export interface CheckpointDbResponse {
  snapshot_path: string;
}

export interface TestConnectionResponse {
  ok: boolean;
  credits?: number;
  error?: string;
}

export interface ContentBlock {
  type: "text" | "image_url" | "tool_use" | "tool_result";
  text?: string;
  url?: string;
  tool_use_id?: string;
  name?: string;
  input?: Record<string, unknown>;
  content?: string;
}

export interface ChatFolder {
  id: string;
  name: string;
  sort_order: number;
  created_at: string;
}

export interface ChatSummary {
  id: string;
  folder_id: string | null;
  title: string;
  model_id: string;
  created_at: string;
  updated_at: string;
}

export interface MessageRecord {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "tool";
  content: ContentBlock[];
  tokens_in: number | null;
  tokens_out: number | null;
  credits: number | null;
  created_at: string;
}

export interface ChatModelInfo {
  id: string;
  display_name: string;
  price_hint: string;
  estimate_credits?: number | null;
  price_updated_at?: string | null;
  supports_vision: boolean;
  supports_tools: boolean;
}

export interface ModelParameter {
  name: string;
  type: "textarea" | "select" | "switch" | "text" | "number" | "image_urls" | "image_url";
  required?: boolean;
  max_length?: number;
  max_items?: number;
  options?: string[];
  default?: string | boolean | number | string[];
  visible_when?: Record<string, unknown>;
  required_when?: Record<string, unknown>;
}

export interface ImageModelInfo {
  id: string;
  display_name: string;
  price_hint: string;
  category: "image" | "video" | "chat" | "audio";
  estimate_credits?: number | null;
  price_updated_at?: string | null;
}

export interface ModelSchema {
  id: string;
  display_name: string;
  price_hint: string;
  estimate_credits?: number | null;
  price_updated_at?: string | null;
  parameters: ModelParameter[];
}

export interface GenerationRecord {
  id: string;
  type: "image" | "video" | "audio";
  model_id: string;
  task_id: string | null;
  status: "pending" | "running" | "success" | "failed";
  prompt: string | null;
  params: Record<string, unknown> | null;
  credits_used: number | null;
  remote_url: string | null;
  local_path: string | null;
  error_msg: string | null;
  created_at: string;
  completed_at: string | null;
  has_file: boolean;
}

export interface SendMessageResponse {
  message_id: string;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  getSystemPaths: () => request<SystemPathsResponse>("/api/v1/system/paths"),

  checkpointDb: () =>
    request<CheckpointDbResponse>("/internal/checkpoint-db", { method: "POST" }),

  getSettings: () => request<AppSettings>("/api/v1/settings"),

  patchSettings: (patch: Partial<AppSettings>) =>
    request<AppSettings>("/api/v1/settings", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  getCredits: () => request<CreditsResponse>("/api/v1/account/credits"),

  getSessionUsage: () => request<SessionUsageResponse>("/api/v1/account/session-usage"),

  resetSession: () =>
    request<void>("/api/v1/account/reset-session", { method: "POST" }),

  testConnection: () =>
    request<TestConnectionResponse>("/api/v1/account/test-connection", {
      method: "POST",
    }),

  reloadApiKey: (apiKey: string) =>
    request<HealthResponse>("/internal/reload-api-key", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    }),

  listChatModels: () => request<ChatModelInfo[]>("/api/v1/chats/models"),

  listFolders: () => request<ChatFolder[]>("/api/v1/chats/folders"),

  createFolder: (name: string) =>
    request<ChatFolder>("/api/v1/chats/folders", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  updateFolder: (folderId: string, name: string) =>
    request<ChatFolder>(`/api/v1/chats/folders/${folderId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  deleteFolder: (folderId: string) =>
    request<void>(`/api/v1/chats/folders/${folderId}`, { method: "DELETE" }),

  listChats: (options?: { folderId?: string | null; q?: string }) => {
    const params = new URLSearchParams();
    if (options?.folderId) params.set("folder_id", options.folderId);
    if (options?.q?.trim()) params.set("q", options.q.trim());
    const query = params.toString();
    return request<ChatSummary[]>(`/api/v1/chats${query ? `?${query}` : ""}`);
  },

  createChat: (modelId: string, folderId?: string | null) =>
    request<ChatSummary>("/api/v1/chats", {
      method: "POST",
      body: JSON.stringify({ model_id: modelId, folder_id: folderId ?? null }),
    }),

  updateChat: (
    chatId: string,
    patch: { title?: string; folder_id?: string | null; model_id?: string },
  ) =>
    request<ChatSummary>(`/api/v1/chats/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteChat: (chatId: string) =>
    request<void>(`/api/v1/chats/${chatId}`, { method: "DELETE" }),

  getMessages: (chatId: string, q?: string) => {
    const query = q?.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
    return request<MessageRecord[]>(`/api/v1/chats/${chatId}/messages${query}`);
  },

  async exportChat(chatId: string): Promise<Blob> {
    const base = await getSidecarUrl();
    const response = await fetch(`${base}/api/v1/chats/${chatId}/export`);
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // ignore
      }
      throw new ApiError(detail, response.status);
    }
    return response.blob();
  },

  sendMessage: (
    chatId: string,
    content: ContentBlock[],
    toolsEnabled = false,
  ) =>
    request<SendMessageResponse>(`/api/v1/chats/${chatId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, tools_enabled: toolsEnabled }),
    }),

  async streamReply(
    chatId: string,
    messageId: string,
    onEvent: StreamHandler,
    options?: { signal?: AbortSignal; toolsEnabled?: boolean },
  ): Promise<void> {
    const base = await getSidecarUrl();
    const params = new URLSearchParams({
      message_id: messageId,
      tools_enabled: String(options?.toolsEnabled ?? false),
    });
    const response = await fetch(
      `${base}/api/v1/chats/${chatId}/stream?${params}`,
      { signal: options?.signal },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // ignore
      }
      throw new ApiError(detail, response.status);
    }
    await consumeSseStream(response, onEvent);
  },

  async uploadChatImage(file: File): Promise<string> {
    const base = await getSidecarUrl();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${base}/api/v1/chats/upload`, {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // ignore
      }
      throw new ApiError(detail, response.status);
    }
    const data = (await response.json()) as { file_url: string };
    return data.file_url;
  },

  listImageModels: () =>
    request<ImageModelInfo[]>("/api/v1/models?type=image"),

  listVideoModels: () =>
    request<ImageModelInfo[]>("/api/v1/models?type=video"),

  listAudioModels: () =>
    request<ImageModelInfo[]>("/api/v1/models?type=audio"),

  getModelSchema: (modelId: string) =>
    request<ModelSchema>(`/api/v1/models/${encodeURIComponent(modelId)}/schema`),

  createGeneration: (modelId: string, input: Record<string, unknown>) =>
    request<GenerationRecord>("/api/v1/generations", {
      method: "POST",
      body: JSON.stringify({ model_id: modelId, input }),
    }),

  listGenerations: (type: "image" | "video" | "audio" = "image") =>
    request<GenerationRecord[]>(`/api/v1/generations?type=${type}`),

  getGeneration: (id: string) =>
    request<GenerationRecord>(`/api/v1/generations/${id}`),

  async getGenerationFileUrl(id: string): Promise<string> {
    const base = await getSidecarUrl();
    return `${base}/api/v1/generations/${id}/file`;
  },

  deleteGeneration: (id: string) =>
    request<void>(`/api/v1/generations/${id}`, { method: "DELETE" }),

  retryGeneration: (id: string) =>
    request<GenerationRecord>(`/api/v1/generations/${id}/retry`, { method: "POST" }),
};
