import type { Threat } from "../utils/types";

const severityStyle: Record<Threat["severity"], string> = {
  low: "text-emerald-300 border-emerald-500/30",
  medium: "text-amber-300 border-amber-500/30",
  high: "text-orange-300 border-orange-500/30",
  critical: "text-rose-300 border-rose-500/30"
};

const severityLabel: Record<Threat["severity"], string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический"
};

type Props = {
  threat: Threat;
};

export function ThreatCard({ threat }: Props) {
  return (
    <article className="rounded-xl border border-cyan-900/40 bg-cyber-card p-4 shadow-glow">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-base font-semibold">{threat.title}</h3>
        <span className={`rounded-full border px-2 py-0.5 text-xs ${severityStyle[threat.severity]}`}>
          {severityLabel[threat.severity]}
        </span>
      </div>
      <p className="text-sm text-slate-300">{threat.description}</p>
    </article>
  );
}
