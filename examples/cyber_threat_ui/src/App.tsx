import { useState } from "react";
import { AskAIPage } from "./pages/ask_ai";
import { DashboardPage } from "./pages/dashboard";
import { NewsPage } from "./pages/news";

type Page = "dashboard" | "news" | "ask_ai";

const tabs: { id: Page; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "news", label: "News" },
  { id: "ask_ai", label: "Ask AI" },
];

export default function App() {
  const [activePage, setActivePage] = useState<Page>("dashboard");

  return (
    <div className="min-h-screen bg-cyber-bg text-slate-100">
      <header className="border-b border-cyan-900/50 bg-cyber-panel">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-bold tracking-wide text-cyan-300">
              Cyber Threat Intelligence
            </h1>
            <p className="text-xs text-cyber-muted">
              Powered by RAG Platform API
            </p>
          </div>
          <span className="rounded-full border border-cyan-800/50 bg-cyan-900/20 px-3 py-1 text-xs text-cyan-300">
            Connected
          </span>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-6 py-6">
        <nav className="w-56 shrink-0 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActivePage(tab.id)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-sm ${
                activePage === tab.id
                  ? "border-cyan-400 bg-cyan-400/10 text-cyan-200"
                  : "border-cyan-900/40 bg-cyber-card text-slate-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <main className="flex-1">
          {activePage === "dashboard" && <DashboardPage />}
          {activePage === "news" && <NewsPage />}
          {activePage === "ask_ai" && <AskAIPage />}
        </main>
      </div>
    </div>
  );
}
