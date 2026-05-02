import type {
  ChatLogEntry,
  ChatResponse,
  IngestionJob,
  Project,
  RagasCompareResponse,
  RagasEvaluateResponse,
  RagasModelsEnvelope,
  Source,
  SourceCreated,
  User,
} from "./types";

function viteMetaEnv(): Record<string, string | boolean | undefined> | undefined {
  return (import.meta as unknown as { env?: Record<string, string | boolean | undefined> }).env;
}

function viteEnvString(key: "VITE_API_URL"): string | undefined {
  const v = viteMetaEnv()?.[key];
  return typeof v === "string" ? v.trim() : undefined;
}

function isViteDev(): boolean {
  return Boolean(viteMetaEnv()?.DEV);
}

/**
 * API base URL.
 * - Vite dev (`npm run dev`, в т.ч. в Docker): относительный `/api/v1` — тот же origin, что у страницы;
 *   запросы проксируются на бэкенд (см. `vite.config.ts`), не нужен доступ к порту 8000 с машины клиента.
 * - Production / preview: если VITE_API_URL указывает на localhost, а страница открыта с LAN-IP,
 *   подставляем hostname страницы и порт 8000; иначе — явный VITE_API_URL.
 */
function getApiBase(): string {
  const env = viteEnvString("VITE_API_URL")?.replace(/\/$/, "");
  if (typeof window !== "undefined" && isViteDev()) {
    return "/api/v1";
  }
  if (typeof window !== "undefined") {
    const bundledIsLoopback = (u: string) => /localhost|127\.0\.0\.1/i.test(u);
    if (!env || bundledIsLoopback(env)) {
      return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
    }
    return env;
  }
  return env || "http://localhost:8000/api/v1";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${body || res.statusText}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

function json(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export type ProjectStats = {
  project_id: number;
  sources_count: number;
  chunks_count: number;
  last_updated: string | null;
};

export type RefreshResult = {
  project_id: number;
  sources_processed: number;
  sources_succeeded?: number;
  sources_failed?: number;
  total_chunks: number;
  errors: string[];
};

export const api = {
  register(email: string, fullName: string, password: string) {
    return request<User>("/auth/register", json({ email, full_name: fullName, password }));
  },

  login(email: string, password: string) {
    return request<{ access_token: string; user: User }>(
      "/auth/login",
      json({ email, password }),
    );
  },

  listProjects(userId?: number) {
    const qs = userId != null ? `?user_id=${userId}` : "";
    return request<Project[]>(`/projects/${qs}`);
  },

  createProject(userId: number, name: string, prompt: string) {
    return request<Project>("/projects/", json({ user_id: userId, name, prompt, settings: {} }));
  },

  updateProject(
    id: number,
    body: Partial<{ name: string; prompt: string | null; settings: Record<string, unknown> }>,
  ) {
    return request<Project>(`/projects/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  deleteProject(id: number) {
    return request<void>(`/projects/${id}`, { method: "DELETE" });
  },

  listSources(projectId: number) {
    return request<Source[]>(`/sources/?project_id=${projectId}`);
  },

  addWebSource(projectId: number, title: string, url: string) {
    return request<SourceCreated>("/sources/web", json({ project_id: projectId, title, url }));
  },

  addTelegramSource(projectId: number, title: string, chatId: string) {
    return request<SourceCreated>(
      "/sources/telegram",
      json({ project_id: projectId, title, chat_id: chatId }),
    );
  },

  addFileSource(projectId: number, title: string, file: File) {
    const fd = new FormData();
    fd.append("project_id", String(projectId));
    fd.append("title", title);
    fd.append("file", file);
    return request<SourceCreated>("/sources/file", { method: "POST", body: fd });
  },

  deleteSource(id: number) {
    return request<void>(`/sources/${id}`, { method: "DELETE" });
  },

  scheduleIngestion(sourceId: number, cron = "0 * * * *") {
    return request<IngestionJob>("/ingestion/schedule", json({ source_id: sourceId, cron }));
  },

  runIngestion(jobId: number) {
    return request<{ job_id: number; chunks_created: number }>(
      `/ingestion/run/${jobId}`,
      json({}),
    );
  },

  refreshProject(projectId: number, trigger: "auto" | "manual" = "auto") {
    const q = trigger === "manual" ? "?trigger=manual" : "?trigger=auto";
    return request<RefreshResult>(`/ingestion/refresh/${projectId}${q}`, { method: "POST" });
  },

  projectStats(projectId: number) {
    return request<ProjectStats>(`/ingestion/stats/${projectId}`);
  },

  chatHistory(projectId: number) {
    return request<ChatLogEntry[]>(`/chat/${projectId}/history`);
  },

  chat(projectId: number, message: string) {
    return request<ChatResponse>(`/chat/${projectId}`, json({ message, top_k: 5 }));
  },

  getRagasModels() {
    return request<RagasModelsEnvelope>("/evaluation/ragas-models");
  },

  /** POST /evaluation/ragas — долгий запрос (LLM-судья RAGAS). */
  runRagasEvaluate(jsonl: string) {
    return request<RagasEvaluateResponse>("/evaluation/ragas", json({ jsonl }));
  },

  /**
   * RAGAS-сравнение: временный индекс по contexts из JSONL, RAG vs прямой LLM (эталон ground_truth).
   */
  runRagasCompare(jsonl: string, opts?: { topK?: number }) {
    const body: Record<string, unknown> = { jsonl };
    if (opts?.topK != null) body.top_k = opts.topK;
    return request<RagasCompareResponse>("/evaluation/ragas-compare", json(body));
  },
};
