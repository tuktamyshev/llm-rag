import { FormEvent, useEffect, useState } from "react";
import { api } from "./api";
import type { Source } from "./types";

type Props = { projectId: number };

export default function SourcesPanel({ projectId }: Props) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [tab, setTab] = useState<"web" | "telegram">("web");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [chatId, setChatId] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => { load(); }, [projectId]);

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
    setAdding(true);
    setError("");
    try {
      if (tab === "web") {
        await api.addWebSource(projectId, title.trim(), url.trim());
      } else {
        await api.addTelegramSource(projectId, title.trim(), chatId.trim());
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

      {error && <p className="src-error">{error}</p>}

      {loading ? (
        <p className="muted">Загрузка источников…</p>
      ) : sources.length === 0 ? (
        <p className="muted">
          Источников пока нет. Добавьте веб-страницу или канал Telegram ниже, затем нажмите
          «Обновить базу знаний», чтобы загрузить данные.
        </p>
      ) : (
        <ul className="source-list">
          {sources.map((s) => (
            <li key={s.id}>
              <span className={`badge ${s.source_type}`}>{s.source_type}</span>
              <span className="source-title">{s.title}</span>
              <span className="source-uri">{s.uri || s.external_id || ""}</span>
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
        ) : (
          <input
            placeholder="@канал, ID чата или https://t.me/channel"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            required
          />
        )}

        <button type="submit" className="btn-primary btn-sm" disabled={adding}>
          {adding ? "Добавление…" : "Добавить источник"}
        </button>
      </form>
    </div>
  );
}
