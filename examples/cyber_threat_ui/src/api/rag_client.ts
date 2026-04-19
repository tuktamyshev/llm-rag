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

const API_BASE = import.meta.env.VITE_RAG_API_URL ?? "http://localhost:8000/api/v1";
const PROJECT_ID = Number(import.meta.env.VITE_PROJECT_ID ?? 1);

export async function askRag(message: string): Promise<ChatApiResponse> {
  const response = await fetch(`${API_BASE}/chat/${PROJECT_ID}`, {
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
  const response = await fetch(`${API_BASE}/chat/${PROJECT_ID}/history?limit=50`);
  if (!response.ok) return [];
  return (await response.json()) as ChatHistoryEntry[];
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/../docs`, { method: "HEAD" });
    return response.ok;
  } catch {
    return false;
  }
}
