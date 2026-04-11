import { FormEvent, useState } from "react";
import { askRag } from "../api/rag_client";
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
      setError(err instanceof Error ? err.message : "Failed to ask AI");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="flex h-[calc(100vh-12rem)] flex-col rounded-2xl border border-cyan-900/40 bg-cyber-panel">
      <header className="border-b border-cyan-900/50 px-5 py-4">
        <h2 className="text-xl font-semibold">Ask AI</h2>
        <p className="text-sm text-cyber-muted">Chat with RAG-powered cyber intelligence assistant.</p>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <p className="text-sm text-cyber-muted">Ask about incidents, IOC triage, or threat actor behavior.</p>
        ) : (
          messages.map((m) => <ChatMessage key={m.id} message={m} />)
        )}
      </div>

      <form onSubmit={onSubmit} className="border-t border-cyan-900/50 p-4">
        <div className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-cyan-900/60 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about latest threats..."
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900 disabled:opacity-50"
          >
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-rose-300">{error}</p>}
      </form>
    </section>
  );
}
