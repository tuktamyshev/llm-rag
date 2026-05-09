import type { RagasCompareResponse, RagasEvaluateResponse, RagasMetricSummary } from "./types";

const EMPTY_METRIC: RagasMetricSummary = {
  samples_count: 0,
  avg_faithfulness: 0,
  avg_relevancy: 0,
  avg_context_precision: 0,
  avg_context_recall: 0,
};

function asMetric(v: unknown): RagasMetricSummary {
  if (!v || typeof v !== "object") return { ...EMPTY_METRIC };
  const o = v as Record<string, unknown>;
  return {
    samples_count: typeof o.samples_count === "number" ? o.samples_count : 0,
    avg_faithfulness: typeof o.avg_faithfulness === "number" ? o.avg_faithfulness : 0,
    avg_relevancy: typeof o.avg_relevancy === "number" ? o.avg_relevancy : 0,
    avg_context_precision: typeof o.avg_context_precision === "number" ? o.avg_context_precision : 0,
    avg_context_recall: typeof o.avg_context_recall === "number" ? o.avg_context_recall : 0,
    raw_scores: o.raw_scores as RagasMetricSummary["raw_scores"],
    error: typeof o.error === "string" ? o.error : null,
  };
}

/** Нормализация ответа сравнения из localStorage (старые baseline / битые объекты). */
function migrateCompareResult(result: unknown): RagasCompareResponse {
  if (result == null || typeof result !== "object") {
    return {
      samples_count: 0,
      rag: { ...EMPTY_METRIC },
      rag_raw: { ...EMPTY_METRIC },
      no_rag: { ...EMPTY_METRIC },
      questions: [],
      rag_answers: [],
      rag_raw_answers: [],
      no_rag_answers: [],
    };
  }
  const r = result as Record<string, unknown>;
  const rag = asMetric(r.rag);
  const rag_raw = asMetric(r.rag_raw);
  const noRagRaw = r.no_rag != null && typeof r.no_rag === "object" ? r.no_rag : r.baseline;
  const no_rag = asMetric(noRagRaw);
  const no_rag_answers = Array.isArray(r.no_rag_answers)
    ? (r.no_rag_answers as string[])
    : Array.isArray(r.baseline_answers)
      ? (r.baseline_answers as string[])
      : [];
  const rag_raw_answers = Array.isArray(r.rag_raw_answers) ? (r.rag_raw_answers as string[]) : [];
  return {
    samples_count: typeof r.samples_count === "number" ? r.samples_count : 0,
    rag,
    rag_raw,
    no_rag,
    questions: Array.isArray(r.questions) ? (r.questions as string[]) : [],
    rag_answers: Array.isArray(r.rag_answers) ? (r.rag_answers as string[]) : [],
    rag_raw_answers,
    no_rag_answers,
    processing: (r.processing as RagasCompareResponse["processing"]) ?? null,
    error: typeof r.error === "string" ? r.error : undefined,
    models: r.models && typeof r.models === "object" && !Array.isArray(r.models) ? (r.models as Record<string, string>) : undefined,
  };
}

const STORAGE_KEY = "llm-rag-ragas-history-v1";
const MAX_ITEMS = 40;
const MAX_JSONL_CHARS = 100_000;

export type RagasHistoryItemRagas = {
  id: string;
  createdAt: string;
  mode: "ragas";
  models: Record<string, string>;
  jsonl: string;
  jsonlTruncated: boolean;
  result: RagasEvaluateResponse;
};

export type RagasHistoryItemCompare = {
  id: string;
  createdAt: string;
  mode: "compare";
  models: Record<string, string>;
  jsonl: string;
  jsonlTruncated: boolean;
  result: RagasCompareResponse;
  /** Проект, для которого считалось сравнение (из models или явно). */
  compareProjectId?: number | null;
};

export type RagasHistoryItem = RagasHistoryItemRagas | RagasHistoryItemCompare;

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function trimJsonl(text: string): { jsonl: string; jsonlTruncated: boolean } {
  if (text.length <= MAX_JSONL_CHARS) return { jsonl: text, jsonlTruncated: false };
  return { jsonl: text.slice(0, MAX_JSONL_CHARS), jsonlTruncated: true };
}

export function loadRagasHistory(): RagasHistoryItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.map((item): RagasHistoryItem => {
      if (!item || typeof item !== "object") return item as RagasHistoryItem;
      const o = item as RagasHistoryItem;
      if (o.mode === "compare") {
        try {
          return { ...o, result: migrateCompareResult((o as RagasHistoryItemCompare).result) } as RagasHistoryItemCompare;
        } catch {
          return { ...(o as object), mode: "compare", result: migrateCompareResult(null) } as RagasHistoryItemCompare;
        }
      }
      return o;
    });
  } catch {
    return [];
  }
}

function saveRagasHistory(items: RagasHistoryItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* quota / private mode */
  }
}

export function clearRagasHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

export function deleteRagasHistoryItem(id: string): RagasHistoryItem[] {
  const next = loadRagasHistory().filter((x) => x.id !== id);
  saveRagasHistory(next);
  return next;
}

export function appendRagasHistoryRagas(jsonl: string, result: RagasEvaluateResponse): RagasHistoryItem[] {
  const { jsonl: j, jsonlTruncated } = trimJsonl(jsonl);
  const item: RagasHistoryItemRagas = {
    id: newId(),
    createdAt: new Date().toISOString(),
    mode: "ragas",
    models: result.models ?? {},
    jsonl: j,
    jsonlTruncated,
    result,
  };
  const next = [item, ...loadRagasHistory()].slice(0, MAX_ITEMS);
  saveRagasHistory(next);
  return next;
}

export function appendRagasHistoryCompare(
  jsonl: string,
  result: RagasCompareResponse,
  opts?: { compareProjectId?: number | null },
): RagasHistoryItem[] {
  const { jsonl: j, jsonlTruncated } = trimJsonl(jsonl);
  const item: RagasHistoryItemCompare = {
    id: newId(),
    createdAt: new Date().toISOString(),
    mode: "compare",
    models: result.models ?? {},
    jsonl: j,
    jsonlTruncated,
    result,
    compareProjectId: opts?.compareProjectId,
  };
  const next = [item, ...loadRagasHistory()].slice(0, MAX_ITEMS);
  saveRagasHistory(next);
  return next;
}
