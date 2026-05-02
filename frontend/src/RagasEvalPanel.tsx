import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";
import RagasHistoryPanel from "./RagasHistoryPanel";
import RagasModelsBlock from "./RagasModelsBlock";
import {
  appendRagasHistoryCompare,
  appendRagasHistoryRagas,
  clearRagasHistory,
  deleteRagasHistoryItem,
  loadRagasHistory,
  type RagasHistoryItem,
  type RagasHistoryItemCompare,
} from "./ragasHistoryStorage";
import { RAGAS_SAMPLE_FILES } from "./ragasSamples";
import type { RagasCompareResponse, RagasEvaluateResponse, RagasMetricSummary } from "./types";

type Loading = "" | "ragas" | "compare";

const EMPTY_RAGAS_METRIC: RagasMetricSummary = {
  samples_count: 0,
  avg_faithfulness: 0,
  avg_relevancy: 0,
  avg_context_precision: 0,
  avg_context_recall: 0,
};

function safeMetric(m: RagasMetricSummary | undefined | null): RagasMetricSummary {
  return m ?? EMPTY_RAGAS_METRIC;
}

function MetricTable({
  title,
  r,
}: {
  title: string;
  r: {
    avg_faithfulness: number;
    avg_relevancy: number;
    avg_context_precision: number;
    avg_context_recall: number;
  };
}) {
  return (
    <div className="ragas-metric-block">
      <h4 className="ragas-metric-block-title">{title}</h4>
      <div className="ragas-metrics ragas-metrics--compact">
        <div className="ragas-metric">
          <span className="ragas-metric-label">Faithfulness</span>
          <span className="ragas-metric-value">{r.avg_faithfulness.toFixed(4)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Answer relevancy</span>
          <span className="ragas-metric-value">{r.avg_relevancy.toFixed(4)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Context precision</span>
          <span className="ragas-metric-value">{r.avg_context_precision.toFixed(4)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Context recall</span>
          <span className="ragas-metric-value">{r.avg_context_recall.toFixed(4)}</span>
        </div>
      </div>
    </div>
  );
}

function answerCellText(text: string | undefined, emptyLabel: string): string {
  const t = (text ?? "").trim();
  return t.length ? t : emptyLabel;
}

function AnswerPairsBlock({ c }: { c: RagasCompareResponse }) {
  const qs = c.questions ?? [];
  const ra = c.rag_answers ?? [];
  const ba = c.no_rag_answers ?? [];
  const n = Math.max(qs.length, ra.length, ba.length);
  if (n === 0) return null;

  return (
    <details className="ragas-raw ragas-raw--pairs">
      <summary>Вопросы: ответ с RAG (временный индекс из contexts) и без RAG (только LLM)</summary>
      <p className="muted ragas-pairs-hint">
        Слева — <strong>retrieval + LLM</strong> по чанкам, проиндексированным из <code>contexts</code> этой строки
        JSONL (временный проект на сервере, после запуска удаляется). Контексты для RAGAS — найденные чанки. Справа —
        прямой ответ модели <em>без</em> документов. Эталон — <code>ground_truth</code>.
      </p>
      <div className="ragas-pairs-wrap">
        {Array.from({ length: n }, (_, i) => (
          <div key={i} className="ragas-answer-pair">
            <p className="ragas-q">
              <strong>Вопрос {i + 1}.</strong> {qs[i] ?? "—"}
            </p>
            <div className="ragas-pair-grid">
              <div className="ragas-pair-col">
                <span className="ragas-pair-label">С RAG (изолированный индекс)</span>
                <pre className="ragas-pre ragas-pre--inline">
                  {answerCellText(ra[i], "Пусто: ответ с RAG для этой строки не получен.")}
                </pre>
              </div>
              <div className="ragas-pair-col">
                <span className="ragas-pair-label">Без RAG (модель без документов)</span>
                <pre className="ragas-pre ragas-pre--inline">
                  {answerCellText(ba[i], "Пусто: ответ без RAG для этой строки не получен.")}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}

export default function RagasEvalPanel() {
  const [jsonl, setJsonl] = useState("");
  const [compareTopK, setCompareTopK] = useState(5);
  const [loading, setLoading] = useState<Loading>("");
  const [result, setResult] = useState<RagasEvaluateResponse | null>(null);
  const [compareResult, setCompareResult] = useState<RagasCompareResponse | null>(null);
  const [localError, setLocalError] = useState("");
  const [serverModels, setServerModels] = useState<Record<string, string> | null>(null);
  const [modelsLoadError, setModelsLoadError] = useState(false);
  const [history, setHistory] = useState<RagasHistoryItem[]>(() => loadRagasHistory());

  useEffect(() => {
    api
      .getRagasModels()
      .then((r) => {
        setServerModels(r.models);
        setModelsLoadError(false);
      })
      .catch(() => {
        setServerModels(null);
        setModelsLoadError(true);
      });
  }, []);

  async function loadSampleFile(path: string) {
    setLocalError("");
    try {
      const res = await fetch(path);
      if (!res.ok) throw new Error(`Не удалось загрузить (${res.status}): ${path}`);
      setJsonl(await res.text());
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "Ошибка загрузки примера");
    }
  }

  function restoreFromHistory(item: RagasHistoryItem) {
    setJsonl(item.jsonl);
    if (item.mode === "ragas") {
      setResult(item.result);
      setCompareResult(null);
      setLocalError(item.result.error ?? "");
    } else {
      const cmp = item as RagasHistoryItemCompare;
      setCompareResult(cmp.result);
      setResult(null);
      setLocalError(cmp.result.error ?? "");
    }
  }

  function handleClearHistory() {
    if (!window.confirm("Удалить всю историю RAGAS на этом устройстве?")) return;
    clearRagasHistory();
    setHistory([]);
  }

  function handleDeleteHistory(id: string) {
    setHistory(deleteRagasHistoryItem(id));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!jsonl.trim()) {
      setLocalError("Вставьте JSONL или загрузите пример");
      return;
    }
    const snapshot = jsonl;
    setLoading("ragas");
    setLocalError("");
    setResult(null);
    setCompareResult(null);
    try {
      const r = await api.runRagasEvaluate(snapshot);
      setResult(r);
      if (r.error) setLocalError(r.error);
      setHistory(appendRagasHistoryRagas(snapshot, r));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Ошибка запроса");
    } finally {
      setLoading("");
    }
  }

  async function runCompare() {
    if (!jsonl.trim()) {
      setLocalError("Вставьте JSONL или загрузите пример");
      return;
    }
    const snapshot = jsonl;
    setLoading("compare");
    setLocalError("");
    setResult(null);
    setCompareResult(null);
    try {
      const r = await api.runRagasCompare(snapshot, { topK: compareTopK });
      setCompareResult(r);
      if (r.error) setLocalError(r.error);
      setHistory(appendRagasHistoryCompare(snapshot, r));
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Ошибка запроса");
    } finally {
      setLoading("");
    }
  }

  const busy = loading !== "";

  return (
    <div className="ragas-panel">
      {modelsLoadError && (
        <p className="muted ragas-models-fetch-err">Не удалось загрузить сведения о моделях с сервера.</p>
      )}
      {serverModels && Object.keys(serverModels).length > 0 && (
        <RagasModelsBlock models={serverModels} title="Модели на сервере (как будет при оценке)" />
      )}

      {busy && serverModels && (
        <div className="ragas-loading-models">
          <p className="ragas-loading-text">
            {loading === "ragas" ? "Считаем RAGAS…" : "Сравнение и RAGAS…"} Используются те же модели, что в блоке выше.
          </p>
        </div>
      )}

      <div className="ragas-toolbar">
        <span className="ragas-toolbar-label muted">Примеры:</span>
        <div className="ragas-sample-chips">
          {RAGAS_SAMPLE_FILES.map((s) => (
            <button
              key={s.path}
              type="button"
              className="btn-chip"
              disabled={busy}
              onClick={() => void loadSampleFile(s.path)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <form onSubmit={onSubmit} className="ragas-form">
        <textarea
          className="ragas-jsonl"
          value={jsonl}
          onChange={(e) => setJsonl(e.target.value)}
          placeholder="Только RAGAS: полный JSONL (question, contexts, ground_truth, answer). Сравнение: question, ground_truth и непустые contexts — по ним поднимается временный индекс для ветки с RAG."
          rows={14}
          disabled={busy}
          spellCheck={false}
        />
        <div className="ragas-compare-options">
          <label className="ragas-topk-label muted">
            top_k для сравнения (ветка с RAG){" "}
            <input
              type="number"
              className="ragas-topk-input"
              min={1}
              max={50}
              value={compareTopK}
              disabled={busy}
              onChange={(e) => setCompareTopK(Math.min(50, Math.max(1, Number(e.target.value) || 5)))}
            />
          </label>
          <span className="muted ragas-compare-project-hint">
            Сравнение: для каждой строки сервер создаёт временный проект, индексирует <code>contexts</code> из файла,
            затем удаляет проект; ветка «без RAG» — тот же вопрос в LLM без документов.
          </span>
        </div>
        <div className="ragas-actions">
          <button type="submit" className="btn-primary" disabled={busy}>
            {loading === "ragas" ? "Считаем метрики…" : "Только RAGAS"}
          </button>
          <button type="button" className="btn-primary btn-secondary-action" disabled={busy} onClick={() => void runCompare()}>
            {loading === "compare" ? "Сравнение…" : "RAGAS: с RAG vs без RAG (эталон в JSONL)"}
          </button>
        </div>
      </form>
      {localError && <div className="toast-error ragas-toast">{localError}</div>}
      {result && !busy && (
        <div className="ragas-results">
          <h3 className="ragas-results-title">Результаты (только ваш датасет)</h3>
          <RagasModelsBlock models={result.models} title="Модели этого запуска" className="ragas-models-inline" />
          <p className="muted">Примеров: {result.samples_count}</p>
          <div className="ragas-metrics">
            <div className="ragas-metric">
              <span className="ragas-metric-label">Faithfulness</span>
              <span className="ragas-metric-value">{result.avg_faithfulness.toFixed(4)}</span>
            </div>
            <div className="ragas-metric">
              <span className="ragas-metric-label">Answer relevancy</span>
              <span className="ragas-metric-value">{result.avg_relevancy.toFixed(4)}</span>
            </div>
            <div className="ragas-metric">
              <span className="ragas-metric-label">Context precision</span>
              <span className="ragas-metric-value">{result.avg_context_precision.toFixed(4)}</span>
            </div>
            <div className="ragas-metric">
              <span className="ragas-metric-label">Context recall</span>
              <span className="ragas-metric-value">{result.avg_context_recall.toFixed(4)}</span>
            </div>
          </div>
          {result.raw_scores && Object.keys(result.raw_scores).length > 0 && (
            <details className="ragas-raw">
              <summary>Сырые оценки по примерам</summary>
              <pre className="ragas-pre">{JSON.stringify(result.raw_scores, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      {compareResult && !busy && (
        <div className="ragas-results ragas-results--compare">
          <h3 className="ragas-results-title">Сравнение RAGAS: с RAG (временный индекс из contexts) vs без RAG</h3>
          <RagasModelsBlock models={compareResult.models} title="Модели этого запуска" className="ragas-models-inline" />
          <p className="muted">Примеров: {compareResult.samples_count}</p>
          <div className="ragas-compare-cols">
            <MetricTable title="С RAG (изолированный индекс)" r={safeMetric(compareResult.rag)} />
            <MetricTable title="Без RAG (только LLM)" r={safeMetric(compareResult.no_rag)} />
          </div>
          <table className="ragas-delta-table" aria-label="Разница метрик: RAG минус вариант без RAG">
            <caption className="sr-only">Разница средних: RAG − без RAG</caption>
            <thead>
              <tr>
                <th>Метрика</th>
                <th>RAG − без RAG</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Faithfulness</td>
                <td>
                  {(safeMetric(compareResult.rag).avg_faithfulness - safeMetric(compareResult.no_rag).avg_faithfulness).toFixed(4)}
                </td>
              </tr>
              <tr>
                <td>Answer relevancy</td>
                <td>
                  {(safeMetric(compareResult.rag).avg_relevancy - safeMetric(compareResult.no_rag).avg_relevancy).toFixed(4)}
                </td>
              </tr>
              <tr>
                <td>Context precision</td>
                <td>
                  {(
                    safeMetric(compareResult.rag).avg_context_precision - safeMetric(compareResult.no_rag).avg_context_precision
                  ).toFixed(4)}
                </td>
              </tr>
              <tr>
                <td>Context recall</td>
                <td>
                  {(safeMetric(compareResult.rag).avg_context_recall - safeMetric(compareResult.no_rag).avg_context_recall).toFixed(4)}
                </td>
              </tr>
            </tbody>
          </table>
          <AnswerPairsBlock c={compareResult} />
        </div>
      )}

      <RagasHistoryPanel items={history} onClearAll={handleClearHistory} onDelete={handleDeleteHistory} onRestore={restoreFromHistory} />
    </div>
  );
}
