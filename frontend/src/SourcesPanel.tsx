import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";
import type { Source, SourceCreated } from "./types";

type Props = { projectId: number };

export default function SourcesPanel({ projectId }: Props) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [tab, setTab] = useState<"web" | "telegram" | "file">("web");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [chatId, setChatId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    setInfo("");
    setError("");
    load();
  }, [projectId]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setSources(await api.listSources(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить источники");
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    if (tab === "file" && !file) {
      setError("Выберите файл");
      return;
    }
    setAdding(true);
    setError("");
    setInfo("");
    try {
      let created: SourceCreated;
      if (tab === "web") {
        created = await api.addWebSource(projectId, title.trim(), url.trim());
      } else if (tab === "telegram") {
        created = await api.addTelegramSource(projectId, title.trim(), chatId.trim());
      } else {
        if (!file) return;
        created = await api.addFileSource(projectId, title.trim(), file);
        setFile(null);
      }
      if (created.ingest_in_background) {
        setInfo(
          "Источник сохранён. Индексация идёт в фоне (первая загрузка модели может занять несколько минут). Через время обновите страницу статистики или нажмите «Обновить базу знаний».",
        );
        setError("");
      } else if (created.ingest_error) {
        setError(`Источник добавлен, но индексация не удалась: ${created.ingest_error}`);
      } else {
        setError("");
        setInfo("");
      }
      setTitle("");
      setUrl("");
      setChatId("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить источник");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await api.deleteSource(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить");
    }
  }

  return (
    <div className="sources-panel">
      <div className="sources-header">
        <h3>Источники данных</h3>
      </div>

      {info && <p className="src-info">{info}</p>}
      {error && <p className="src-error">{error}</p>}

      {loading ? (
        <p className="muted">Загрузка источников…</p>
      ) : sources.length === 0 ? (
        <p className="muted">
          Источников пока нет. Добавьте веб-страницу, файл или канал Telegram ниже, затем нажмите
          «Обновить базу знаний», чтобы загрузить данные.
        </p>
      ) : (
        <ul className="source-list">
          {sources.map((s) => (
            <li key={s.id}>
              <span className={`badge ${s.source_type}`}>{s.source_type}</span>
              <span className="source-title">{s.title}</span>
              <span className="source-uri">
                {s.source_type === "file" && typeof s.settings?.original_filename === "string"
                  ? s.settings.original_filename
                  : s.uri || s.external_id || ""}
              </span>
              <button className="btn-icon" onClick={() => handleDelete(s.id)} title="Удалить источник">
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <form className="add-source-form" onSubmit={handleAdd}>
        <div className="tab-switch">
          <button type="button" className={tab === "web" ? "active" : ""} onClick={() => setTab("web")}>
            Веб-URL
          </button>
          <button type="button" className={tab === "telegram" ? "active" : ""} onClick={() => setTab("telegram")}>
            Telegram
          </button>
          <button type="button" className={tab === "file" ? "active" : ""} onClick={() => setTab("file")}>
            Файл
          </button>
        </div>

        <input
          placeholder="Название источника"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />

        {tab === "web" ? (
          <input
            type="url"
            placeholder="https://example.com/article"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        ) : tab === "telegram" ? (
          <input
            placeholder="@канал, ID чата или https://t.me/channel"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            required
          />
        ) : (
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,.csv,.json,.xml,.html,.rtf,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        )}

        <button type="submit" className="btn-primary btn-sm" disabled={adding}>
          {adding ? "Добавление…" : "Добавить источник"}
        </button>
      </form>
    </div>
  );
}
