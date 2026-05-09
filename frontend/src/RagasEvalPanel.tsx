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
import type {
  CompareProcessingStats,
  IngestStageAggregate,
  IngestStageStats,
  RagasCompareResponse,
  RagasEvaluateResponse,
  RagasMetricSummary,
} from "./types";

function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "0 Б";
  const units = ["Б", "КБ", "МБ", "ГБ"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v >= 100 ? 0 : v >= 10 ? 1 : 2)} ${units[i]}`;
}

function fmtSeconds(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n >= 1) return `${n.toFixed(2)} с`;
  return `${(n * 1000).toFixed(0)} мс`;
}

function fmtNumber(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("ru-RU").format(n);
}

function ProcessingAggregateCard({ title, agg }: { title: string; agg: IngestStageAggregate }) {
  const reduction =
    agg.raw_chars_total > 0
      ? ((agg.raw_chars_total - agg.cleaned_chars_total) / agg.raw_chars_total) * 100
      : 0;
  return (
    <div className="ragas-metric-block">
      <h4 className="ragas-metric-block-title">{title}</h4>
      <div className="ragas-metrics ragas-metrics--compact">
        <div className="ragas-metric">
          <span className="ragas-metric-label">Сбор + предобработка</span>
          <span className="ragas-metric-value">{fmtSeconds(agg.collect_preproc_seconds_total)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Векторизация (всего)</span>
          <span className="ragas-metric-value">{fmtSeconds(agg.vectorize_seconds_total)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Сырые данные (символов)</span>
          <span className="ragas-metric-value">{fmtNumber(agg.raw_chars_total)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">После предобработки</span>
          <span className="ragas-metric-value">
            {fmtNumber(agg.cleaned_chars_total)}
            {reduction !== 0 && (
              <span className="muted ragas-delta-inline"> ({reduction > 0 ? "−" : "+"}{Math.abs(reduction).toFixed(1)}%)</span>
            )}
          </span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Чанков всего</span>
          <span className="ragas-metric-value">{fmtNumber(agg.chunks_count_total)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Размерность вектора</span>
          <span className="ragas-metric-value">{fmtNumber(agg.vector_dim)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Объём векторов (float32)</span>
          <span className="ragas-metric-value">{fmtBytes(agg.vector_total_bytes)}</span>
        </div>
        <div className="ragas-metric">
          <span className="ragas-metric-label">Среднее на пример</span>
          <span className="ragas-metric-value">
            {fmtSeconds(agg.collect_preproc_seconds_avg)} + {fmtSeconds(agg.vectorize_seconds_avg)}
          </span>
        </div>
      </div>
    </div>
  );
}

function ProcessingPerSampleTable({ rows }: { rows: IngestStageStats[] }) {
  if (!rows.length) return null;
  return (
    <details className="ragas-raw">
      <summary>Метрики обработки по примерам ({rows.length})</summary>
      <table className="ragas-delta-table" aria-label="Метрики обработки по примерам">
        <thead>
          <tr>
            <th>#</th>
            <th>Сырые</th>
            <th>После очистки</th>
            <th>Чанков</th>
            <th>Сбор + предобр.</th>
            <th>Векторизация</th>
            <th>Объём векторов</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <td>{fmtNumber(r.raw_chars)}</td>
              <td>{fmtNumber(r.cleaned_chars)}</td>
              <td>{fmtNumber(r.chunks_count)}</td>
              <td>{fmtSeconds(r.collect_preproc_seconds)}</td>
              <td>{fmtSeconds(r.vectorize_seconds)}</td>
              <td>{fmtBytes(r.vector_total_bytes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function ProcessingBlock({ p }: { p: CompareProcessingStats }) {
  return (
    <div className="ragas-results-section">
      <h4 className="ragas-results-subtitle">Обработка данных (тайминги и объёмы)</h4>
      <div className="ragas-compare-cols">
        <ProcessingAggregateCard title="Стандартный пайплайн" agg={p.standard} />
        <ProcessingAggregateCard title="Raw (без очистки + naive‑чанк)" agg={p.raw} />
      </div>
      <ProcessingPerSampleTable rows={p.per_sample_standard} />
      <ProcessingPerSampleTable rows={p.per_sample_raw} />
    </div>
  );
}

type Loading = "" | "ragas" | "compare" | "compare-urls";

const URLS_SAMPLE = [
  "https://ru.wikipedia.org/wiki/Retrieval-augmented_generation",
  "https://ru.wikipedia.org/wiki/Большие_языковые_модели",
].join("\n");

const URLS_SAMPLE_JSONL = [
  '{"question": "Что такое Retrieval-Augmented Generation?", "ground_truth": "RAG — подход, при котором языковая модель получает дополнительные тексты из внешней базы и опирается на них при генерации ответа."}',
  '{"question": "Чем большие языковые модели отличаются от обычных нейросетей?", "ground_truth": "LLM — это нейросети с очень большим числом параметров, обученные на огромных корпусах текста; они умеют генерировать связный текст и обобщать знания из обучающей выборки."}',
].join("\n");

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
  const rr = c.rag_raw_answers ?? [];
  const ba = c.no_rag_answers ?? [];
  const n = Math.max(qs.length, ra.length, rr.length, ba.length);
  if (n === 0) return null;
  const hasRaw = rr.length > 0;

  return (
    <details className="ragas-raw ragas-raw--pairs">
      <summary>
        Вопросы: ответ с RAG (standard{hasRaw ? " + raw" : ""}) и без RAG (только LLM)
      </summary>
      <p className="muted ragas-pairs-hint">
        Контексты RAG строятся из <code>contexts</code> в JSONL (временный проект, после прогона удаляется).
        В режиме <strong>standard</strong> — очистка + рекурсивное чанкование; <strong>raw</strong> — без очистки и
        с naive‑чанком фиксированной длины. Эталон для RAGAS — <code>ground_truth</code>.
      </p>
      <div className="ragas-pairs-wrap">
        {Array.from({ length: n }, (_, i) => (
          <div key={i} className="ragas-answer-pair">
            <p className="ragas-q">
              <strong>Вопрос {i + 1}.</strong> {qs[i] ?? "—"}
            </p>
            <div className="ragas-pair-grid">
              <div className="ragas-pair-col">
                <span className="ragas-pair-label">С RAG (standard)</span>
                <pre className="ragas-pre ragas-pre--inline">
                  {answerCellText(ra[i], "Пусто: ответ standard‑RAG не получен.")}
                </pre>
              </div>
              {hasRaw && (
                <div className="ragas-pair-col">
                  <span className="ragas-pair-label">С RAG (raw, без обработки)</span>
                  <pre className="ragas-pre ragas-pre--inline">
                    {answerCellText(rr[i], "Пусто: ответ raw‑RAG не получен.")}
                  </pre>
                </div>
              )}
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
  const [urlsText, setUrlsText] = useState("");
  const [urlsJsonl, setUrlsJsonl] = useState("");
  const [urlsBlockOpen, setUrlsBlockOpen] = useState(true);

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

  function fillUrlsSample() {
    setUrlsText(URLS_SAMPLE);
    setUrlsJsonl(URLS_SAMPLE_JSONL);
    setLocalError("");
  }

  async function runCompareUrls() {
    const urls = urlsText
      .split(/\r?\n/)
      .map((u) => u.trim())
      .filter((u) => u.length > 0);
    if (urls.length === 0) {
      setLocalError("Добавьте хотя бы один URL (по одному на строке).");
      return;
    }
    if (!urlsJsonl.trim()) {
      setLocalError("Вставьте список вопросов и эталонов в формате JSONL (поля question, ground_truth).");
      return;
    }
    const snapshot = urlsJsonl;
    setLoading("compare-urls");
    setLocalError("");
    setResult(null);
    setCompareResult(null);
    try {
      const r = await api.runRagasCompareUrls(urls, snapshot, { topK: compareTopK });
      setCompareResult(r);
      if (r.error) setLocalError(r.error);
      setHistory(
        appendRagasHistoryCompare(`__URLS__\n${urls.join("\n")}\n---\n${snapshot}`, r),
      );
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
            {loading === "ragas"
              ? "Считаем RAGAS…"
              : loading === "compare-urls"
                ? "Скачиваем URL, индексируем и считаем RAGAS…"
                : "Сравнение и RAGAS…"}{" "}
            Используются те же модели, что в блоке выше.
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

      <details
        className="ragas-urls-block"
        open={urlsBlockOpen}
        onToggle={(e) => setUrlsBlockOpen(e.currentTarget.open)}
      >
        <summary className="ragas-urls-summary">
          Свой пример: задайте URL и вопросы — запустится тот же compare на «живых» страницах
        </summary>
        <p className="muted ragas-urls-hint">
          Бэкенд скачает каждую ссылку как обычный <strong>WEB‑источник</strong>, поднимет два временных проекта
          (<em>standard</em> и <em>raw</em>), проиндексирует все URL и ответит на ваши вопросы. После прогона
          проекты удаляются. Для метрик RAGAS нужен <code>ground_truth</code> на каждый вопрос.
        </p>
        <div className="ragas-urls-grid">
          <label className="ragas-urls-label">
            <span className="muted">URL (по одному на строке, до 10):</span>
            <textarea
              className="ragas-jsonl ragas-urls-input"
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              placeholder={"https://ru.wikipedia.org/wiki/Retrieval-augmented_generation\nhttps://example.com/article"}
              rows={5}
              disabled={busy}
              spellCheck={false}
            />
          </label>
          <label className="ragas-urls-label">
            <span className="muted">Вопросы и эталоны (JSONL, поля question и ground_truth):</span>
            <textarea
              className="ragas-jsonl ragas-urls-input"
              value={urlsJsonl}
              onChange={(e) => setUrlsJsonl(e.target.value)}
              placeholder={'{"question": "…", "ground_truth": "…"}\n{"question": "…", "ground_truth": "…"}'}
              rows={8}
              disabled={busy}
              spellCheck={false}
            />
          </label>
        </div>
        <div className="ragas-actions">
          <button type="button" className="btn-chip" disabled={busy} onClick={fillUrlsSample}>
            Заполнить примером
          </button>
          <button
            type="button"
            className="btn-primary btn-secondary-action"
            disabled={busy}
            onClick={() => void runCompareUrls()}
          >
            {loading === "compare-urls" ? "Скачиваем и считаем…" : "RAGAS на моих URL"}
          </button>
        </div>
      </details>

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
          <h3 className="ragas-results-title">
            Сравнение RAGAS: с RAG (standard) vs с RAG (raw, без обработки) vs без RAG
          </h3>
          <RagasModelsBlock models={compareResult.models} title="Модели этого запуска" className="ragas-models-inline" />
          <p className="muted">Примеров: {compareResult.samples_count}</p>
          <div className="ragas-compare-cols">
            <MetricTable title="С RAG (standard)" r={safeMetric(compareResult.rag)} />
            <MetricTable title="С RAG (raw, без обработки)" r={safeMetric(compareResult.rag_raw)} />
            <MetricTable title="Без RAG (только LLM)" r={safeMetric(compareResult.no_rag)} />
          </div>
          <table className="ragas-delta-table" aria-label="Разница метрик">
            <caption className="sr-only">Разница средних</caption>
            <thead>
              <tr>
                <th>Метрика</th>
                <th>standard − raw</th>
                <th>standard − без RAG</th>
                <th>raw − без RAG</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Faithfulness", "avg_faithfulness"],
                ["Answer relevancy", "avg_relevancy"],
                ["Context precision", "avg_context_precision"],
                ["Context recall", "avg_context_recall"],
              ].map(([label, key]) => {
                const k = key as keyof RagasMetricSummary;
                const std = safeMetric(compareResult.rag)[k] as number;
                const raw = safeMetric(compareResult.rag_raw)[k] as number;
                const nr = safeMetric(compareResult.no_rag)[k] as number;
                return (
                  <tr key={key}>
                    <td>{label}</td>
                    <td>{(std - raw).toFixed(4)}</td>
                    <td>{(std - nr).toFixed(4)}</td>
                    <td>{(raw - nr).toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {compareResult.processing && <ProcessingBlock p={compareResult.processing} />}
          <AnswerPairsBlock c={compareResult} />
        </div>
      )}

      <RagasHistoryPanel items={history} onClearAll={handleClearHistory} onDelete={handleDeleteHistory} onRestore={restoreFromHistory} />
    </div>
  );
}
