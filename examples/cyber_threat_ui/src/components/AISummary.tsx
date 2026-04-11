type Props = {
  text: string | null;
  loading: boolean;
  onGenerate: () => void;
};

export function AISummary({ text, loading, onGenerate }: Props) {
  return (
    <section className="rounded-xl border border-cyan-800/40 bg-cyber-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-200">AI Summary</h3>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="rounded-md bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-slate-900 disabled:opacity-60"
        >
          {loading ? "Generating..." : "AI Summary"}
        </button>
      </div>
      <p className="text-sm text-slate-200">
        {text ?? "No summary yet. Click AI Summary to ask RAG for a short brief."}
      </p>
    </section>
  );
}
