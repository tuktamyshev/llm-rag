import type { RagasHistoryItem } from "./ragasHistoryStorage";

type Props = {
  items: RagasHistoryItem[];
  onClearAll: () => void;
  onDelete: (id: string) => void;
  onRestore: (item: RagasHistoryItem) => void;
};

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function f2(n: unknown): string {
  return (typeof n === "number" && !Number.isNaN(n) ? n : 0).toFixed(2);
}

function summaryLine(item: RagasHistoryItem): string {
  if (item.mode === "ragas") {
    const r = item.result;
    return `${r.samples_count ?? 0} пр. · F=${f2(r.avg_faithfulness)} AR=${f2(r.avg_relevancy)}`;
  }
  const r = item.result;
  const rf = f2(r.rag?.avg_faithfulness);
  const bf = f2(r.no_rag?.avg_faithfulness);
  return `${r.samples_count ?? 0} пр. · RAG F=${rf} / без RAG F=${bf}`;
}

export default function RagasHistoryPanel({ items, onClearAll, onDelete, onRestore }: Props) {
  if (items.length === 0) {
    return (
      <div className="ragas-history ragas-history--empty">
        <span className="muted">История запусков пуста — после успешного расчёта запись появится здесь.</span>
      </div>
    );
  }

  return (
    <div className="ragas-history">
      <div className="ragas-history-header">
        <h3 className="ragas-history-title">История ({items.length})</h3>
        <button type="button" className="btn-ghost btn-sm danger-text" onClick={onClearAll}>
          Очистить всё
        </button>
      </div>
      <ul className="ragas-history-list">
        {items.map((item) => (
          <li key={item.id} className="ragas-history-row">
            <div className="ragas-history-main">
              <span className="ragas-history-badge">{item.mode === "ragas" ? "RAGAS" : "Сравнение RAG / без RAG"}</span>
              <span className="ragas-history-time">{fmtTime(item.createdAt)}</span>
              <span className="ragas-history-summary muted">{summaryLine(item)}</span>
              {item.jsonlTruncated && <span className="ragas-history-trunc">JSONL обрезан при сохранении</span>}
            </div>
            <div className="ragas-history-actions">
              <button type="button" className="btn-ghost btn-sm" onClick={() => onRestore(item)}>
                Открыть
              </button>
              <button type="button" className="btn-ghost btn-sm danger-text" onClick={() => onDelete(item.id)}>
                Удалить
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
