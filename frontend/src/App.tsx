import { FormEvent, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "./api";
import type { ProjectStats, RefreshResult } from "./api";
import LoginPage from "./LoginPage";
import SourcesPanel from "./SourcesPanel";
import type { ChatMessage, Project, User } from "./types";

const AUTH_KEY = "llm-rag-auth";

function ingestionFromProject(p: Project | undefined): { hours: number; cooldownSec: number } {
  if (!p?.settings || typeof p.settings !== "object") return { hours: 12, cooldownSec: 300 };
  const ing = (p.settings as Record<string, unknown>).ingestion;
  if (!ing || typeof ing !== "object") return { hours: 12, cooldownSec: 300 };
  const obj = ing as Record<string, unknown>;
  const hours = typeof obj.auto_refresh_interval_hours === "number" ? obj.auto_refresh_interval_hours : 12;
  const cooldownSec =
    typeof obj.manual_refresh_cooldown_seconds === "number" ? obj.manual_refresh_cooldown_seconds : 300;
  return { hours, cooldownSec };
}

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

  const [draftAutoHours, setDraftAutoHours] = useState(12);
  const [draftCooldownSec, setDraftCooldownSec] = useState(300);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [manualBlockedUntil, setManualBlockedUntil] = useState<number | null>(null);
  const [, setCooldownTick] = useState(0);
  const [showSchedule, setShowSchedule] = useState(false);
  const [schedulePopoverPos, setSchedulePopoverPos] = useState<{ top: number; right: number } | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const scheduleToolbarRef = useRef<HTMLDivElement>(null);
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
        msgs.push({ ...mkMsg("assistant", h.answer), ts: h.created_at });
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

  const activeProject = projects.find((p) => p.id === projectId);
  const appliedSchedule = ingestionFromProject(activeProject);

  useEffect(() => {
    const p = projects.find((x) => x.id === projectId);
    const { hours, cooldownSec } = ingestionFromProject(p);
    setDraftAutoHours(hours);
    setDraftCooldownSec(cooldownSec);
  }, [projectId, projects]);

  useEffect(() => {
    setShowSchedule(false);
    setSchedulePopoverPos(null);
  }, [projectId]);

  useLayoutEffect(() => {
    if (!showSchedule) {
      setSchedulePopoverPos(null);
      return;
    }
    const el = scheduleToolbarRef.current;
    if (!el) return;

    const update = () => {
      const r = el.getBoundingClientRect();
      setSchedulePopoverPos({
        top: r.bottom + 8,
        right: Math.max(16, window.innerWidth - r.right),
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [showSchedule]);

  useEffect(() => {
    if (!showSchedule) return;
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowSchedule(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [showSchedule]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    if (!manualBlockedUntil) return;
    if (Date.now() >= manualBlockedUntil) {
      setManualBlockedUntil(null);
      return;
    }
    const id = setInterval(() => {
      setCooldownTick((t) => t + 1);
      setManualBlockedUntil((u) => {
        if (!u || Date.now() >= u) return null;
        return u;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [manualBlockedUntil]);

  useEffect(() => {
    if (!projectId) return;
    const ms = Math.max(60_000, appliedSchedule.hours * 3600 * 1000);
    autoRef.current = setInterval(() => {
      api
        .refreshProject(projectId, "auto")
        .then((r) => {
          setLastRefresh(r);
          loadStats(projectId);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Ошибка автообновления базы");
        });
    }, ms);
    return () => clearInterval(autoRef.current);
  }, [projectId, loadStats, appliedSchedule.hours]);

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
    if (manualBlockedUntil && Date.now() < manualBlockedUntil) return;
    setRefreshing(true);
    setError("");
    setLastRefresh(null);
    try {
      const result = await api.refreshProject(projectId, "manual");
      setLastRefresh(result);
      if (result.errors?.length) {
        const failed = result.sources_failed ?? result.errors.length;
        const ok = result.sources_succeeded ?? result.sources_processed - result.errors.length;
        setError(
          `Сбор данных завершён с ошибками: не удалось обработать ${failed} из ${result.sources_processed} источников (${ok} успешно). Подробности — ниже.`,
        );
      } else {
        setError("");
      }
      loadStats(projectId);
      const cd = ingestionFromProject(projects.find((p) => p.id === projectId)).cooldownSec;
      if (cd > 0) setManualBlockedUntil(Date.now() + cd * 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить базу");
    } finally {
      setRefreshing(false);
    }
  }

  async function saveSchedule(e: FormEvent) {
    e.preventDefault();
    if (!projectId || !activeProject || savingSchedule) return;
    setSavingSchedule(true);
    setError("");
    try {
      const prev = (activeProject.settings ?? {}) as Record<string, unknown>;
      const prevIng = (prev.ingestion ?? {}) as Record<string, unknown>;
      const settings = {
        ...prev,
        ingestion: {
          ...prevIng,
          auto_refresh_interval_hours: draftAutoHours,
          manual_refresh_cooldown_seconds: draftCooldownSec,
        },
      };
      const updated = await api.updateProject(projectId, { settings });
      setProjects((prevList) => prevList.map((p) => (p.id === updated.id ? updated : p)));
      setShowSchedule(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить расписание");
    } finally {
      setSavingSchedule(false);
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
      setMessages((prev) => [...prev, mkMsg("assistant", res.answer)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setSending(false);
    }
  }

  if (!user) return <LoginPage onAuth={handleAuth} />;

  const project = projects.find((p) => p.id === projectId);
  const manualRemainingSec =
    manualBlockedUntil && Date.now() < manualBlockedUntil
      ? Math.max(0, Math.ceil((manualBlockedUntil - Date.now()) / 1000))
      : 0;
  const manualButtonDisabled =
    refreshing || (!!manualBlockedUntil && Date.now() < manualBlockedUntil);

  const schedulePopover =
    showSchedule &&
    projectId &&
    schedulePopoverPos &&
    createPortal(
      <>
        <div
          className="schedule-backdrop"
          role="presentation"
          aria-hidden
          onClick={() => setShowSchedule(false)}
        />
        <div
          className="schedule-popover"
          role="dialog"
          aria-modal={true}
          aria-labelledby="schedule-heading"
          style={{
            position: "fixed",
            top: schedulePopoverPos.top,
            right: schedulePopoverPos.right,
            zIndex: 400,
          }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <form className="schedule-panel" onSubmit={saveSchedule}>
            <span className="schedule-label" id="schedule-heading">
              Расписание обновления
            </span>
            <label className="schedule-field">
              Автообновление, ч
              <input
                type="number"
                min={0.25}
                max={8760}
                step={0.25}
                value={draftAutoHours}
                onChange={(e) => setDraftAutoHours(Number(e.target.value))}
              />
            </label>
            <label className="schedule-field">
              Пауза между ручными обновлениями, с
              <input
                type="number"
                min={0}
                max={86400}
                step={1}
                value={draftCooldownSec}
                onChange={(e) => setDraftCooldownSec(Number(e.target.value))}
              />
            </label>
            <button type="submit" className="btn-primary btn-sm" disabled={savingSchedule}>
              {savingSchedule ? "Сохранение…" : "Сохранить"}
            </button>
            <span className="muted schedule-hint">
              По умолчанию авто каждые 12 ч; интервал авто не короче 1 мин.
            </span>
          </form>
        </div>
      </>,
      document.body,
    );

  return (
    <>
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
              <div className="header-toolbar" ref={scheduleToolbarRef}>
                <div className="header-actions">
                  <button
                    type="button"
                    className={`btn-schedule-toggle${showSchedule ? " active" : ""}`}
                    onClick={() => setShowSchedule((v) => !v)}
                    aria-expanded={showSchedule}
                    title="Настройки расписания обновления базы"
                  >
                    Расписание
                  </button>
                  <button
                    type="button"
                    className={`btn-refresh${refreshing ? " spinning" : ""}`}
                    onClick={handleRefresh}
                    disabled={manualButtonDisabled}
                    title={
                      manualRemainingSec > 0
                        ? `Доступно через ${manualRemainingSec} с`
                        : "Собрать данные из всех источников и обновить базу знаний"
                    }
                  >
                    {refreshing ? "Сбор данных…" : manualRemainingSec > 0 ? `Подождите ${manualRemainingSec} с` : "Обновить базу знаний"}
                  </button>
                </div>
              </div>
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
            <div
              className={`ingestion-result${(lastRefresh.errors?.length ?? 0) ? " ingestion-result--errors" : ""}`}
              role={lastRefresh.errors?.length ? "alert" : "status"}
            >
              <div className="ingestion-result-summary">
                <strong>
                  {(lastRefresh.errors?.length ?? 0)
                    ? "Обновление завершено с ошибками по источникам"
                    : "База знаний обновлена"}
                </strong>
                {" — "}
                успешно{" "}
                {lastRefresh.sources_succeeded ??
                  lastRefresh.sources_processed - (lastRefresh.errors?.length ?? 0)}{" "}
                из {lastRefresh.sources_processed} источников, фрагментов: {lastRefresh.total_chunks}
              </div>
              {(lastRefresh.errors?.length ?? 0) > 0 && (
                <ul className="ingestion-result-errors">
                  {lastRefresh.errors!.map((msg, i) => (
                    <li key={`${i}-${msg.slice(0, 40)}`}>{msg}</li>
                  ))}
                </ul>
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
    {schedulePopover}
    </>
  );
}
