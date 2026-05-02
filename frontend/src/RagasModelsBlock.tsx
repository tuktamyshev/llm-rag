import { RAGAS_MODEL_LABELS } from "./ragasModelLabels";

type Props = {
  models: Record<string, string> | undefined | null;
  title?: string;
  className?: string;
};

export default function RagasModelsBlock({ models, title = "Модели и эндпоинты", className }: Props) {
  if (!models || Object.keys(models).length === 0) return null;
  return (
    <div className={`ragas-models-block${className ? ` ${className}` : ""}`}>
      <span className="ragas-models-title">{title}</span>
      <ul className="ragas-models-list">
        {Object.entries(models).map(([key, value]) => (
          <li key={key}>
            <span className="ragas-models-k">{RAGAS_MODEL_LABELS[key] ?? key}</span>
            <code className="ragas-models-v">{value}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}
