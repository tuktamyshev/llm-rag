export type User = {
  id: number;
  email: string;
  full_name: string;
};

export type Project = {
  id: number;
  user_id: number;
  name: string;
  prompt: string | null;
  settings: Record<string, unknown>;
};

export type Source = {
  id: number;
  project_id: number;
  source_type: "web" | "telegram" | "file";
  title: string;
  external_id: string | null;
  uri: string | null;
  settings: Record<string, unknown>;
};

/** Ответ POST /sources/* после первичной индексации */
export type SourceCreated = Source & {
  ingest_error?: string | null;
  chunks_indexed?: number;
  ingest_in_background?: boolean;
};

export type IngestionJob = {
  id: number;
  source_id: number;
  cron: string;
  status: string;
};

export type ChatLogEntry = {
  id: number;
  project_id: number;
  question: string;
  answer: string;
  sources: string[];
  created_at: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  ts: string;
};

export type ChatResponse = {
  answer: string;
  sources?: string[];
};
