import type { ChatLogEntry, ChatResponse, IngestionJob, Project, Source, User } from "./types";

const API =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
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

  deleteProject(id: number) {
    return request<void>(`/projects/${id}`, { method: "DELETE" });
  },

  listSources(projectId: number) {
    return request<Source[]>(`/sources/?project_id=${projectId}`);
  },

  addWebSource(projectId: number, title: string, url: string) {
    return request<Source>("/sources/web", json({ project_id: projectId, title, url }));
  },

  addTelegramSource(projectId: number, title: string, chatId: string) {
    return request<Source>(
      "/sources/telegram",
      json({ project_id: projectId, title, chat_id: chatId }),
    );
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

  refreshProject(projectId: number) {
    return request<RefreshResult>(`/ingestion/refresh/${projectId}`, { method: "POST" });
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
};
