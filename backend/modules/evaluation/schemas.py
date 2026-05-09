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


class IngestStageStats(BaseModel):
    """Тайминги/объёмы стадий пайплайна для одной строки JSONL."""

    mode: str = "standard"
    raw_chars: int = 0
    cleaned_chars: int = 0
    chunks_count: int = 0
    chunks_total_chars: int = 0
    vector_dim: int = 0
    vector_total_bytes: int = 0
    collect_seconds: float = 0.0
    clean_seconds: float = 0.0
    chunk_seconds: float = 0.0
    collect_preproc_seconds: float = 0.0
    vectorize_seconds: float = 0.0


class IngestStageAggregate(BaseModel):
    """Агрегированные метрики по всем строкам для одного режима (standard/raw)."""

    mode: str = "standard"
    samples_count: int = 0
    raw_chars_total: int = 0
    cleaned_chars_total: int = 0
    chunks_count_total: int = 0
    chunks_total_chars_total: int = 0
    vector_dim: int = 0
    vector_total_bytes: int = 0
    collect_preproc_seconds_total: float = 0.0
    vectorize_seconds_total: float = 0.0
    collect_preproc_seconds_avg: float = 0.0
    vectorize_seconds_avg: float = 0.0


class CompareProcessingStats(BaseModel):
    """Метрики обработки данных для compare (по двум режимам)."""

    standard: IngestStageAggregate = Field(default_factory=lambda: IngestStageAggregate(mode="standard"))
    raw: IngestStageAggregate = Field(default_factory=lambda: IngestStageAggregate(mode="raw"))
    per_sample_standard: list[IngestStageStats] = Field(default_factory=list)
    per_sample_raw: list[IngestStageStats] = Field(default_factory=list)


class RagasCompareResponse(BaseModel):
    """
    RAGAS:
    - ветка «с RAG (standard)» — стандартный пайплайн (clean + recursive chunking);
    - ветка «с RAG (raw)» — без очистки и с naive‑чанком фиксированной длины;
    - ветка «без RAG» — прямой LLM без документов.
    Все оцениваются относительно ground_truth из JSONL.
    """

    samples_count: int = 0
    rag: RagasMetricSummary = Field(default_factory=RagasMetricSummary)
    rag_raw: RagasMetricSummary = Field(
        default_factory=RagasMetricSummary,
        description="Метрики варианта с RAG, но без предобработки (raw + naive chunking).",
    )
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
        description="Ответы ветки с RAG (стандартный пайплайн).",
    )
    rag_raw_answers: list[str] = Field(
        default_factory=list,
        description="Ответы ветки с RAG (raw‑режим: без очистки и с naive‑чанком).",
    )
    no_rag_answers: list[str] = Field(
        default_factory=list,
        description="Ответы варианта без RAG (только общие знания LLM).",
    )
    processing: CompareProcessingStats | None = Field(
        default=None,
        description="Метрики обработки данных по обеим веткам RAG (время, объёмы).",
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


class RagasCompareUrlsRequest(BaseModel):
    """
    Сравнение RAGAS на «живых» URL: бэкенд скачивает каждую ссылку как WEB-источник во временный проект
    (отдельные проекты для standard и raw‑режимов), затем выполняет RAG по всем переданным вопросам.

    Тело: `urls` (1..10), `jsonl` со строками `{question, ground_truth}`, опциональный `top_k`.
    `contexts`/`answer` в строках JSONL не используются.
    """

    model_config = ConfigDict(extra="ignore")

    urls: list[str] = Field(..., min_length=1, max_length=10)
    jsonl: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50, description="Число чанков при поиске для ветки с RAG.")
