export type SideTab = "projects" | "sources" | "ragas";

type Props = {
  value: SideTab;
  onChange: (tab: SideTab) => void;
  className?: string;
};

export default function SideTabBar({ value, onChange, className }: Props) {
  return (
    <div className={`side-tabs${className ? ` ${className}` : ""}`} role="tablist" aria-label="Разделы приложения">
      <button
        type="button"
        role="tab"
        aria-selected={value === "projects"}
        className={value === "projects" ? "active" : ""}
        onClick={() => onChange("projects")}
      >
        Проекты
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "sources"}
        className={value === "sources" ? "active" : ""}
        onClick={() => onChange("sources")}
      >
        Источники
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "ragas"}
        className={value === "ragas" ? "active" : ""}
        onClick={() => onChange("ragas")}
      >
        RAGAS
      </button>
    </div>
  );
}
