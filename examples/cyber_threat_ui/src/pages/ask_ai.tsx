import { FormEvent, useEffect, useRef, useState } from "react";
import { askRag, getChatHistory } from "../api/rag_client";
import { ChatMessage } from "../components/ChatMessage";
import type { ChatEntry } from "../utils/types";

function makeId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function AskAIPage() {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory().then((history) => {
      if (history.length === 0) return;
      const entries: ChatEntry[] = [];
      for (const h of history) {
        entries.push({ id: `h-q-${h.id}`, role: "user", text: h.question });
        entries.push({
          id: `h-a-${h.id}`,
          role: "assistant",
          text: h.answer,
          sources: h.sources,
        });
      }
      setMessages(entries);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { id: makeId(), role: "user", text }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const response = await askRag(text);
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "assistant", text: response.answer, sources: response.sources ?? [] },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось получить ответ");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="flex h-[calc(100vh-12rem)] flex-col rounded-2xl border border-cyan-900/40 bg-cyber-panel">
      <header className="border-b border-cyan-900/50 px-5 py-4">
        <h2 className="text-xl font-semibold">Спросить ИИ</h2>
        <p className="text-sm text-cyber-muted">Чат с ассистентом по киберразведке на базе RAG.</p>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-cyber-muted">Спросите об инцидентах, IOC, поведении злоумышленников.</p>
          </div>
        ) : (
          messages.map((m) => <ChatMessage key={m.id} message={m} />)
        )}
        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-cyber-card px-4 py-3">
              <div className="flex gap-1">
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:0ms]" />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:150ms]" />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="border-t border-cyan-900/50 p-4">
        {error && (
          <p className="mb-2 rounded-lg border border-rose-800/50 bg-rose-900/20 px-3 py-2 text-sm text-rose-300">
            {error}
          </p>
        )}
        <div className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-cyan-900/60 bg-slate-900 px-3 py-2 text-sm outline-none placeholder:text-slate-500 focus:border-cyan-400"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Спросите о последних угрозах…"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900 transition-opacity disabled:opacity-50"
          >
            {sending ? "…" : "Отправить"}
          </button>
        </div>
      </form>
    </section>
  );
}
