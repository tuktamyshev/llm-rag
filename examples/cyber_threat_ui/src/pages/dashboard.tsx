import { ThreatCard } from "../components/ThreatCard";
import { mockThreats } from "../utils/mock_data";

export function DashboardPage() {
  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold">Панель угроз</h2>
        <p className="mt-1 text-sm text-cyber-muted">Актуальная картина киберугроз для вашего проекта.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {mockThreats.map((threat) => (
          <ThreatCard key={threat.id} threat={threat} />
        ))}
      </div>
    </section>
  );
}
