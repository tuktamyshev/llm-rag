import type { NewsItem } from "../utils/types";

type Props = {
  items: NewsItem[];
};

export function NewsFeed({ items }: Props) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <article key={item.id} className="rounded-xl border border-cyan-900/40 bg-cyber-card p-4">
          <h3 className="text-base font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-wide text-cyber-muted">{item.source}</p>
          <p className="mt-2 text-sm text-slate-300">{item.text}</p>
        </article>
      ))}
    </div>
  );
}
