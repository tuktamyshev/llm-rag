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

export type RagasEvaluateResponse = {
  samples_count: number;
  avg_faithfulness: number;
  avg_relevancy: number;
  avg_context_precision: number;
  avg_context_recall: number;
  raw_scores?: Record<string, number[]> | null;
  error?: string | null;
  models?: Record<string, string>;
};

export type RagasMetricSummary = {
  samples_count: number;
  avg_faithfulness: number;
  avg_relevancy: number;
  avg_context_precision: number;
  avg_context_recall: number;
  raw_scores?: Record<string, number[]> | null;
  error?: string | null;
};

export type IngestStageStats = {
  mode: "standard" | "raw" | string;
  raw_chars: number;
  cleaned_chars: number;
  chunks_count: number;
  chunks_total_chars: number;
  vector_dim: number;
  vector_total_bytes: number;
  collect_seconds: number;
  clean_seconds: number;
  chunk_seconds: number;
  collect_preproc_seconds: number;
  vectorize_seconds: number;
};

export type IngestStageAggregate = {
  mode: "standard" | "raw" | string;
  samples_count: number;
  raw_chars_total: number;
  cleaned_chars_total: number;
  chunks_count_total: number;
  chunks_total_chars_total: number;
  vector_dim: number;
  vector_total_bytes: number;
  collect_preproc_seconds_total: number;
  vectorize_seconds_total: number;
  collect_preproc_seconds_avg: number;
  vectorize_seconds_avg: number;
};

export type CompareProcessingStats = {
  standard: IngestStageAggregate;
  raw: IngestStageAggregate;
  per_sample_standard: IngestStageStats[];
  per_sample_raw: IngestStageStats[];
};

export type RagasCompareResponse = {
  samples_count: number;
  rag: RagasMetricSummary;
  rag_raw: RagasMetricSummary;
  no_rag: RagasMetricSummary;
  questions: string[];
  rag_answers: string[];
  rag_raw_answers: string[];
  no_rag_answers: string[];
  processing?: CompareProcessingStats | null;
  error?: string | null;
  models?: Record<string, string>;
};

export type RagasModelsEnvelope = {
  models: Record<string, string>;
};
