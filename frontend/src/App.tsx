import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ProjectStats, RefreshResult } from "./api";
import LoginPage from "./LoginPage";
import SourcesPanel from "./SourcesPanel";
import type { ChatMessage, Project, User } from "./types";

const AUTH_KEY = "llm-rag-auth";
const AUTO_REFRESH_MS = 60 * 60 * 1000;

function mkMsg(role: "user" | "assistant", text: string): ChatMessage {
  return { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, role, text, ts: new Date().toISOString() };
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState("");

  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPrompt, setNewPrompt] = useState("Ассистент по киберугрозам и интеллекту");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const [sideTab, setSideTab] = useState<"projects" | "sources">("projects");

  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<RefreshResult | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const autoRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    try {
      const saved = localStorage.getItem(AUTH_KEY);
      if (saved) {
        const { user: u, token: t } = JSON.parse(saved);
        setUser(u);
        setToken(t);
      }
    } catch { /* noop */ }
  }, []);

  useEffect(() => {
    if (!user) return;
    api.listProjects(user.id).then((p) => {
      setProjects(p);
      if (p.length && !projectId) setProjectId(p[0].id);
    }).catch(() => {});
  }, [user]);

  const loadStats = useCallback((pid: number) => {
    api.projectStats(pid).then(setStats).catch(() => setStats(null));
  }, []);

  useEffect(() => {
    if (projectId) loadStats(projectId);
    else setStats(null);
  }, [projectId, loadStats]);

  const loadHistory = useCallback(async (pid: number) => {
    try {
      const history = await api.chatHistory(pid);
      const msgs: ChatMessage[] = [];
      for (const h of history) {
        msgs.push(mkMsg("user", h.question));
        const answer = h.sources?.length
          ? `${h.answer}\n\nИсточники:\n${h.sources.map((s) => `• ${s}`).join("\n")}`
          : h.answer;
        msgs.push({ ...mkMsg("assistant", answer), ts: h.created_at });
      }
      setMessages(msgs);
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    if (projectId) loadHistory(projectId);
    else setMessages([]);
  }, [projectId, loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    if (!projectId) return;
    autoRef.current = setInterval(() => {
      api.refreshProject(projectId).then((r) => {
        setLastRefresh(r);
        loadStats(projectId);
      }).catch(() => {});
    }, AUTO_REFRESH_MS);
    return () => clearInterval(autoRef.current);
  }, [projectId, loadStats]);

  function handleAuth(u: User, t: string) {
    setUser(u);
    setToken(t);
    localStorage.setItem(AUTH_KEY, JSON.stringify({ user: u, token: t }));
  }

  function logout() {
    setUser(null); setToken(""); setProjects([]); setProjectId(null); setMessages([]);
    localStorage.removeItem(AUTH_KEY);
  }

  async function createProject(e: FormEvent) {
    e.preventDefault();
    if (!user || !newName.trim()) return;
    try {
      const p = await api.createProject(user.id, newName.trim(), newPrompt.trim());
      setProjects((prev) => [p, ...prev]);
      setProjectId(p.id);
      setNewName("");
      setShowNewProject(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function handleRefresh() {
    if (!projectId || refreshing) return;
    setRefreshing(true);
    setError("");
    setLastRefresh(null);
    try {
      const result = await api.refreshProject(projectId);
      setLastRefresh(result);
      loadStats(projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить базу");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending || !projectId) return;
    setInput("");
    setSending(true);
    setError("");
    setMessages((prev) => [...prev, mkMsg("user", text)]);
    try {
      const res = await api.chat(projectId, text);
      const answer = res.sources?.length
        ? `${res.answer}\n\nИсточники:\n${res.sources.map((s) => `• ${s}`).join("\n")}`
        : res.answer;
      setMessages((prev) => [...prev, mkMsg("assistant", answer)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSending(false);
    }
  }

  if (!user) return <LoginPage onAuth={handleAuth} />;

  const project = projects.find((p) => p.id === projectId);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-top">
          <h1>Платформа RAG</h1>
          <div className="user-badge">
            <span>{user.full_name}</span>
            <button className="btn-link-sm" onClick={logout}>Выйти</button>
          </div>
        </div>

        <div className="side-tabs">
          <button className={sideTab === "projects" ? "active" : ""} onClick={() => setSideTab("projects")}>
            Проекты
          </button>
          <button className={sideTab === "sources" ? "active" : ""} onClick={() => setSideTab("sources")}>
            Источники
          </button>
        </div>

        {sideTab === "projects" && (
          <div className="side-content">
            <button className="btn-new" onClick={() => setShowNewProject(!showNewProject)}>
              + Новый проект
            </button>

            {showNewProject && (
              <form className="new-project-form" onSubmit={createProject}>
                <input placeholder="Название проекта" value={newName} onChange={(e) => setNewName(e.target.value)} required autoFocus />
                <textarea placeholder="Системный промпт" value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)} rows={2} />
                <div className="form-actions">
                  <button type="submit" className="btn-primary btn-sm">Создать</button>
                  <button type="button" className="btn-ghost btn-sm" onClick={() => setShowNewProject(false)}>Отмена</button>
                </div>
              </form>
            )}

            <div className="project-list">
              {projects.map((p) => (
                <button
                  key={p.id}
                  className={`project-item${p.id === projectId ? " active" : ""}`}
                  onClick={() => setProjectId(p.id)}
                  type="button"
                >
                  <span className="project-name">{p.name}</span>
                </button>
              ))}
              {projects.length === 0 && <p className="muted">Пока нет проектов</p>}
            </div>
          </div>
        )}

        {sideTab === "sources" && projectId && (
          <div className="side-content">
            <SourcesPanel projectId={projectId} />
          </div>
        )}
        {sideTab === "sources" && !projectId && (
          <p className="muted pad">Сначала выберите проект</p>
        )}
      </aside>

      <main className="chat-area">
        <header className="chat-header">
          <div className="header-row">
            <div>
              <h2>{project?.name ?? "Выберите проект"}</h2>
              {project?.prompt && <p className="header-prompt">{project.prompt}</p>}
            </div>
            {projectId && (
              <button
                className={`btn-refresh${refreshing ? " spinning" : ""}`}
                onClick={handleRefresh}
                disabled={refreshing}
                title="Собрать данные из всех источников и обновить базу знаний"
              >
                {refreshing ? "Сбор данных…" : "Обновить базу знаний"}
              </button>
            )}
          </div>

          {projectId && stats && (
            <div className="status-bar">
              <div className="stat">
                <span className={`dot${stats.chunks_count > 0 ? " green" : " gray"}`} />
                <span>{stats.chunks_count} фрагментов</span>
              </div>
              <div className="stat">
                <span>Источников: {stats.sources_count}</span>
              </div>
              {stats.last_updated && (
                <div className="stat">
                  Обновлено {new Date(stats.last_updated).toLocaleString("ru-RU")}
                </div>
              )}
              {!stats.last_updated && stats.sources_count > 0 && (
                <div className="stat warn">Ещё не загружено</div>
              )}
            </div>
          )}

          {lastRefresh && (
            <div className={`refresh-toast${lastRefresh.errors.length ? " has-errors" : ""}`}>
              Обработано источников: {lastRefresh.sources_processed}, создано фрагментов: {lastRefresh.total_chunks}
              {lastRefresh.errors.length > 0 && (
                <span className="refresh-errors"> | Ошибки: {lastRefresh.errors.join("; ")}</span>
              )}
            </div>
          )}
        </header>

        <div className="messages-scroll">
          <div className="messages">
            {messages.length === 0 && (
              <p className="empty-state">
                {projectId
                  ? stats && stats.chunks_count === 0
                    ? <>Добавьте источники в боковой панели и нажмите <strong>«Обновить базу знаний»</strong>.</>
                    : "Пока нет сообщений. Задайте вопрос!"
                  : "Выберите проект в боковой панели."}
              </p>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`msg ${m.role}`}>
                <div className="msg-avatar">{m.role === "user" ? "Вы" : "ИИ"}</div>
                <div className="msg-content">
                  <div className="msg-bubble">{m.text}</div>
                  <span className="msg-time">{formatTime(m.ts)}</span>
                </div>
              </div>
            ))}

            {sending && (
              <div className="typing-indicator">
                <div className="msg-avatar" style={{ background: "linear-gradient(135deg, #374151, #4b5563)", width: 34, height: 34, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#fff", flexShrink: 0 }}>ИИ</div>
                <div className="typing-dots">
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {error && <div className="toast-error">{error}</div>}

        <form className="composer" onSubmit={handleSend}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={projectId ? "Введите вопрос…" : "Сначала выберите проект"}
            disabled={sending || !projectId}
            rows={2}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(e); }
            }}
          />
          <button type="submit" disabled={sending || !input.trim() || !projectId}>
            {sending ? "…" : "Отправить"}
          </button>
        </form>
      </main>
    </div>
  );
}
