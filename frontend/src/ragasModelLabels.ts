/** Подписи к ключам `models` из API оценки RAGAS. */
export const RAGAS_MODEL_LABELS: Record<string, string> = {
  ragas_judge_llm: "LLM-судья RAGAS (OpenRouter)",
  openrouter_api_base: "Базовый URL OpenRouter",
  ragas_embedding_model: "Эмбеддинги для answer relevancy (HuggingFace)",
  no_rag_generation_llm: "Генерация ответа без RAG — только LLM (OpenRouter)",
  // Старые записи истории до переименования ключа в API
  baseline_generation_llm: "Генерация ответа без RAG — только LLM (OpenRouter)",
};

export function formatRagasModels(models: Record<string, string> | undefined | null): string {
  if (!models || Object.keys(models).length === 0) return "";
  return Object.entries(models)
    .map(([k, v]) => `${RAGAS_MODEL_LABELS[k] ?? k}: ${v}`)
    .join(" · ");
}
