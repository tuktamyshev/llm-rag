export type ChatApiResponse = {
  answer: string;
  sources?: string[];
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
    throw new Error(`RAG API request failed: ${response.status}`);
  }

  return (await response.json()) as ChatApiResponse;
}
