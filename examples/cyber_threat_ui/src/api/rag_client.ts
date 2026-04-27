export type ChatApiResponse = {
  answer: string;
  sources?: string[];
};

export type ChatHistoryEntry = {
  id: number;
  project_id: number;
  question: string;
  answer: string;
  sources: string[];
  created_at: string;
};

function viteMetaEnv(): Record<string, string | boolean | undefined> | undefined {
  return (import.meta as unknown as { env?: Record<string, string | boolean | undefined> }).env;
}

function viteEnvString(key: "VITE_RAG_API_URL"): string | undefined {
  const v = viteMetaEnv()?.[key];
  return typeof v === "string" ? v.trim() : undefined;
}

function isViteDev(): boolean {
  return Boolean(viteMetaEnv()?.DEV);
}

/** См. основной frontend `getApiBase`: LAN + Docker без прямого доступа к :8000 с клиента. */
function getRagApiBase(): string {
  const env = viteEnvString("VITE_RAG_API_URL")?.replace(/\/$/, "");
  if (typeof window !== "undefined" && isViteDev()) {
    return "/api/v1";
  }
  if (typeof window !== "undefined") {
    const bundledIsLoopback = (u: string) => /localhost|127\.0\.0\.1/i.test(u);
    if (!env || bundledIsLoopback(env)) {
      return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
    }
    return env;
  }
  return env || "http://localhost:8000/api/v1";
}

function getDocsHeadUrl(): string {
  const base = getRagApiBase().replace(/\/$/, "");
  if (base.startsWith("/")) {
    return "/docs";
  }
  const root = base.endsWith("/api/v1") ? base.slice(0, -"/api/v1".length) : base;
  return `${root}/docs`;
}

const PROJECT_ID = Number(viteMetaEnv()?.VITE_PROJECT_ID ?? 1);

export async function askRag(message: string): Promise<ChatApiResponse> {
  const response = await fetch(`${getRagApiBase()}/chat/${PROJECT_ID}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const body = await response.text();
    if (response.status === 429 || body.includes("429") || body.includes("Rate limit")) {
      throw new Error("Превышен лимит запросов — попробуйте позже или пополните баланс OpenRouter");
    }
    if (response.status === 502) {
      throw new Error("Сервис LLM недоступен — проверьте ключ OpenRouter или лимиты");
    }
    throw new Error(`Ошибка API RAG: ${response.status}`);
  }

  return (await response.json()) as ChatApiResponse;
}

export async function getChatHistory(): Promise<ChatHistoryEntry[]> {
  const response = await fetch(`${getRagApiBase()}/chat/${PROJECT_ID}/history?limit=50`);
  if (!response.ok) return [];
  return (await response.json()) as ChatHistoryEntry[];
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(getDocsHeadUrl(), { method: "HEAD" });
    return response.ok;
  } catch {
    return false;
  }
}
