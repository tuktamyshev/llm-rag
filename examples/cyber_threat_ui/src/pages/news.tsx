import { useMemo, useState } from "react";
import { askRag } from "../api/rag_client";
import { AISummary } from "../components/AISummary";
import { NewsFeed } from "../components/NewsFeed";
import { mockNews } from "../utils/mock_data";

export function NewsPage() {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const prompt = useMemo(() => {
    const newsText = mockNews.map((n) => `- ${n.title}: ${n.text}`).join("\n");
    return `Кратко перечисли 5 пунктов для аналитика SOC по этим новостям о киберугрозах:\n${newsText}`;
  }, []);

  async function generateSummary() {
    setLoading(true);
    setError(null);
    try {
      const result = await askRag(prompt);
      setSummary(result.answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сформировать сводку");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold">Новости и разведка</h2>
        <p className="mt-1 text-sm text-cyber-muted">Лента с краткой сводкой на базе ИИ.</p>
      </header>
      <AISummary text={summary} loading={loading} onGenerate={generateSummary} />
      {error && <p className="text-sm text-rose-300">{error}</p>}
      <NewsFeed items={mockNews} />
    </section>
  );
}
