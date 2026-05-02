from pydantic import BaseModel, ConfigDict, Field


class RagasEvaluateRequest(BaseModel):
    """JSONL text: one JSON object per line with question, contexts, ground_truth, answer."""

    jsonl: str = Field(..., min_length=1, description="JSONL dataset (same format as sample_dataset.jsonl)")


class RagasEvaluateResponse(BaseModel):
    samples_count: int
    avg_faithfulness: float
    avg_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    raw_scores: dict | None = None
    error: str | None = None
    models: dict[str, str] = Field(
        default_factory=dict,
        description="Модели/эндпоинты расчёта (из env на момент запроса).",
    )


class RagasModelsPublicResponse(BaseModel):
    """Публичные имена моделей для UI до запуска оценки (без секретов)."""

    models: dict[str, str]


class RagasMetricSummary(BaseModel):
    """Сводка метрик RAGAS по одному набору ответов."""

    samples_count: int = 0
    avg_faithfulness: float = 0.0
    avg_relevancy: float = 0.0
    avg_context_precision: float = 0.0
    avg_context_recall: float = 0.0
    raw_scores: dict | None = None
    error: str | None = None


class RagasCompareResponse(BaseModel):
    """
    RAGAS: ветка «с RAG» (retrieval + LLM по проекту) и ветка «без RAG» (прямой запрос в LLM без документов);
    обе оцениваются относительно ground_truth из JSONL.
    """

    samples_count: int = 0
    rag: RagasMetricSummary = Field(default_factory=RagasMetricSummary)
    no_rag: RagasMetricSummary = Field(
        default_factory=RagasMetricSummary,
        description="Метрики варианта без RAG (только LLM, без документов).",
    )
    questions: list[str] = Field(
        default_factory=list,
        description="Вопросы в порядке оценённых примеров.",
    )
    rag_answers: list[str] = Field(
        default_factory=list,
        description="Ответы ветки с RAG (из пайплайна проекта).",
    )
    no_rag_answers: list[str] = Field(
        default_factory=list,
        description="Ответы варианта без RAG (только общие знания LLM).",
    )
    error: str | None = None
    models: dict[str, str] = Field(default_factory=dict)


class RagasCompareRequest(BaseModel):
    """
    Сравнение RAGAS: для каждой строки — временный проект с индексацией `contexts` из файла, затем retrieval+LLM;
    параллельно прямой LLM без документов. Нужны question, ground_truth и непустые contexts.
    Владелец временных проектов: env `RAGAS_COMPARE_USER_ID` (по умолчанию 1).
    """

    model_config = ConfigDict(extra="ignore")

    jsonl: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50, description="Число чанков при поиске для ветки с RAG.")
    project_id: int | None = Field(
        default=None,
        description="Устарело: не используется (сравнение на временных проектах из contexts в JSONL).",
    )
