from __future__ import annotations

import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from modules.evaluation.schemas import (
    CompareProcessingStats,
    IngestStageAggregate,
    IngestStageStats,
    RagasCompareResponse,
    RagasEvaluateResponse,
    RagasMetricSummary,
)

if TYPE_CHECKING:
    from modules.ingestion.service import IngestionService, IngestStageMetrics
    from modules.projects.service import ProjectService
    from modules.rag.service import RAGService
    from modules.sources.repository import SourceRepository
    from modules.users.repository import UserRepository

logger = logging.getLogger(__name__)

# Max payload size (characters) to limit LLM cost / request time
MAX_JSONL_CHARS = 512_000
MAX_SAMPLES = 80

NO_RAG_SYSTEM_PROMPT = (
    "Ты отвечаешь на вопрос пользователя только из общих знаний, без доступа к какой-либо базе "
    "документов и без ссылки на внутренние источники. Ответь кратко и по существу, на том же языке, "
    "что и вопрос."
)

# Фиктивный контекст для ветки «без RAG»: RAGAS требует непустой список; context_* здесь не про ретривал.
NO_DOCUMENT_CONTEXT = (
    "Документный контекст не предоставлялся; ответ сгенерирован моделью только по общим знаниям."
)

EMPTY_RETRIEVAL_CONTEXT = (
    "Релевантных фрагментов в индексе проекта не найдено; ответ сгенерирован моделью по пустому контексту."
)


def build_ragas_models_metadata(*, include_no_rag_llm: bool = False) -> dict[str, str]:
    """Имена моделей из окружения (для ответа API и UI). Без секретов."""
    judge = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    api_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    emb = os.getenv("RAGAS_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    out: dict[str, str] = {
        "ragas_judge_llm": judge,
        "openrouter_api_base": api_base,
        "ragas_embedding_model": emb,
    }
    if include_no_rag_llm:
        out["no_rag_generation_llm"] = judge
    return out


def _repo_root() -> Path:
    """llm-rag repository root (parent of `evaluation/` and `backend/`)."""
    return Path(__file__).resolve().parents[3]


def _ensure_evaluation_importable() -> None:
    root = _repo_root()
    sroot = str(root)
    if sroot not in sys.path:
        sys.path.insert(0, sroot)
    if not (root / "evaluation" / "ragas").is_dir():
        raise RuntimeError(
            "Пакет evaluation не найден. Запускайте API из корня репозитория llm-rag с PYTHONPATH=.. "
            "или убедитесь, что каталог evaluation скопирован в образ рядом с backend.",
        )


def _load_samples_from_jsonl_string(jsonl: str) -> tuple[list[Any] | None, str | None]:
    """Разбор JSONL в список EvalSample. При ошибке возвращает (None, сообщение)."""
    text = jsonl.strip()
    if not text:
        return None, "Пустой датасет"
    if len(jsonl) > MAX_JSONL_CHARS:
        return None, f"Слишком большой файл: максимум {MAX_JSONL_CHARS} символов"

    _ensure_evaluation_importable()
    from evaluation.ragas.dataset_builder import build_dataset_from_jsonl

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", encoding="utf-8", delete=False) as tmp:
        tmp.write(jsonl)
        tmp_path = tmp.name

    try:
        dataset = build_dataset_from_jsonl(tmp_path)
    except Exception as exc:
        logger.exception("Failed to parse JSONL")
        return None, f"Ошибка разбора JSONL: {exc}"
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if len(dataset) > MAX_SAMPLES:
        return None, f"Слишком много примеров: максимум {MAX_SAMPLES}"

    return dataset, None


def _result_to_summary(samples_count: int, result) -> RagasMetricSummary:
    return RagasMetricSummary(
        samples_count=samples_count,
        avg_faithfulness=result.avg_faithfulness,
        avg_relevancy=result.avg_relevancy,
        avg_context_precision=result.avg_context_precision,
        avg_context_recall=result.avg_context_recall,
        raw_scores=result.raw_scores,
    )


def _compare_pair_lists(rag_samples: list[Any]) -> tuple[list[str], list[str]]:
    return (
        [s.question for s in rag_samples],
        [s.answer if s.answer is not None else "" for s in rag_samples],
    )


def _stats_from_ingest_metrics(m: "IngestStageMetrics") -> IngestStageStats:
    return IngestStageStats(
        mode=m.mode,
        raw_chars=m.raw_chars,
        cleaned_chars=m.cleaned_chars,
        chunks_count=m.chunks_count,
        chunks_total_chars=m.chunks_total_chars,
        vector_dim=m.vector_dim,
        vector_total_bytes=m.vector_total_bytes,
        collect_seconds=round(m.collect_seconds, 6),
        clean_seconds=round(m.clean_seconds, 6),
        chunk_seconds=round(m.chunk_seconds, 6),
        collect_preproc_seconds=round(m.collect_preproc_seconds, 6),
        vectorize_seconds=round(m.vectorize_seconds, 6),
    )


def _fmt_bytes_short(n: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            return f"{v:.1f}{u}"
        v /= 1024
    return f"{n}B"


def _log_compare_aggregate(label: str, agg: IngestStageAggregate) -> None:
    """Сводный лог по всем источникам одного режима compare‑прогона (виден в `docker compose logs backend`)."""
    logger.info(
        "ragas-compare[%s] sources=%d "
        "| collect+preproc total=%.3fs avg=%.3fs vectorize total=%.3fs avg=%.3fs "
        "| raw_chars=%d cleaned_chars=%d chunks=%d chunks_chars=%d "
        "| vector_dim=%d vectors_size=%s",
        label,
        agg.samples_count,
        agg.collect_preproc_seconds_total,
        agg.collect_preproc_seconds_avg,
        agg.vectorize_seconds_total,
        agg.vectorize_seconds_avg,
        agg.raw_chars_total,
        agg.cleaned_chars_total,
        agg.chunks_count_total,
        agg.chunks_total_chars_total,
        agg.vector_dim,
        _fmt_bytes_short(agg.vector_total_bytes),
    )


def _aggregate(mode: str, items: list[IngestStageStats]) -> IngestStageAggregate:
    if not items:
        return IngestStageAggregate(mode=mode)
    n = len(items)
    raw_total = sum(i.raw_chars for i in items)
    clean_total = sum(i.cleaned_chars for i in items)
    chunks_count = sum(i.chunks_count for i in items)
    chunks_chars = sum(i.chunks_total_chars for i in items)
    vector_total_bytes = sum(i.vector_total_bytes for i in items)
    cp_total = sum(i.collect_preproc_seconds for i in items)
    vec_total = sum(i.vectorize_seconds for i in items)
    return IngestStageAggregate(
        mode=mode,
        samples_count=n,
        raw_chars_total=raw_total,
        cleaned_chars_total=clean_total,
        chunks_count_total=chunks_count,
        chunks_total_chars_total=chunks_chars,
        vector_dim=next((i.vector_dim for i in items if i.vector_dim), 0),
        vector_total_bytes=vector_total_bytes,
        collect_preproc_seconds_total=round(cp_total, 6),
        vectorize_seconds_total=round(vec_total, 6),
        collect_preproc_seconds_avg=round(cp_total / n, 6) if n else 0.0,
        vectorize_seconds_avg=round(vec_total / n, 6) if n else 0.0,
    )


def _run_compare_core(
    rag_samples: list[Any],
    rag_raw_samples: list[Any] | None,
    *,
    models: dict[str, str],
    processing: CompareProcessingStats | None = None,
) -> RagasCompareResponse:
    """RAGAS на трёх ветках: standard RAG, raw RAG (опц.), no-RAG (LLM без документов)."""
    from evaluation.ragas.dataset_builder import EvalSample
    from evaluation.ragas.evaluator import RagasEvaluator
    from infrastructure.llm.openrouter import OpenRouterLLMClient

    questions, rag_answers = _compare_pair_lists(rag_samples)
    rag_raw_answers: list[str] = []
    if rag_raw_samples:
        _, rag_raw_answers = _compare_pair_lists(rag_raw_samples)

    llm = OpenRouterLLMClient()
    no_rag_answers: list[str] = []
    try:
        for s in rag_samples:
            no_rag_answers.append(
                llm.generate(
                    prompt=s.question,
                    system_prompt=NO_RAG_SYSTEM_PROMPT,
                )
            )
    except RuntimeError as exc:
        logger.exception("No-RAG (LLM-only) generation failed")
        return RagasCompareResponse(
            samples_count=len(rag_samples),
            questions=questions,
            rag_answers=rag_answers,
            rag_raw_answers=rag_raw_answers,
            processing=processing,
            error=f"Не удалось получить ответы варианта без RAG: {exc}",
            models=models,
        )

    no_rag_samples = [
        EvalSample(
            question=s.question,
            contexts=[NO_DOCUMENT_CONTEXT],
            ground_truth=s.ground_truth,
            answer=ba,
        )
        for s, ba in zip(rag_samples, no_rag_answers, strict=True)
    ]

    evaluator = RagasEvaluator()
    try:
        rag_result = evaluator.evaluate(rag_samples)
    except Exception as exc:
        logger.exception("RAGAS on RAG samples failed")
        return RagasCompareResponse(
            samples_count=len(rag_samples),
            questions=questions,
            rag_answers=rag_answers,
            rag_raw_answers=rag_raw_answers,
            no_rag_answers=no_rag_answers,
            processing=processing,
            error=f"Ошибка RAGAS (ветка RAG): {exc}",
            models=models,
        )

    rag_raw_summary = RagasMetricSummary()
    if rag_raw_samples:
        try:
            raw_result = evaluator.evaluate(rag_raw_samples)
            rag_raw_summary = _result_to_summary(raw_result.samples_count, raw_result)
        except Exception as exc:
            logger.exception("RAGAS on raw RAG samples failed")
            rag_raw_summary = RagasMetricSummary(error=f"Ошибка RAGAS (ветка raw RAG): {exc}")

    try:
        no_rag_result = evaluator.evaluate(no_rag_samples)
    except Exception as exc:
        logger.exception("RAGAS on no-RAG samples failed")
        return RagasCompareResponse(
            samples_count=len(rag_samples),
            questions=questions,
            rag_answers=rag_answers,
            rag_raw_answers=rag_raw_answers,
            rag=_result_to_summary(rag_result.samples_count, rag_result),
            rag_raw=rag_raw_summary,
            no_rag_answers=no_rag_answers,
            processing=processing,
            error=f"Ошибка RAGAS (ветка без RAG): {exc}",
            models=models,
        )

    return RagasCompareResponse(
        samples_count=len(rag_samples),
        questions=questions,
        rag_answers=rag_answers,
        rag_raw_answers=rag_raw_answers,
        rag=_result_to_summary(rag_result.samples_count, rag_result),
        rag_raw=rag_raw_summary,
        no_rag=_result_to_summary(no_rag_result.samples_count, no_rag_result),
        no_rag_answers=no_rag_answers,
        processing=processing,
        models=models,
    )


def run_ragas_from_jsonl(jsonl: str) -> RagasEvaluateResponse:
    models = build_ragas_models_metadata()
    logger.info("ragas[only] start: jsonl_chars=%d", len(jsonl or ""))
    dataset, err = _load_samples_from_jsonl_string(jsonl)
    if err:
        return RagasEvaluateResponse(
            samples_count=0,
            avg_faithfulness=0.0,
            avg_relevancy=0.0,
            avg_context_precision=0.0,
            avg_context_recall=0.0,
            error=err,
            models=models,
        )

    from evaluation.ragas.evaluator import RagasEvaluator

    try:
        result = RagasEvaluator().evaluate(dataset)
    except Exception as exc:
        logger.exception("RAGAS evaluate failed")
        return RagasEvaluateResponse(
            samples_count=len(dataset),
            avg_faithfulness=0.0,
            avg_relevancy=0.0,
            avg_context_precision=0.0,
            avg_context_recall=0.0,
            error=str(exc),
            models=models,
        )

    return RagasEvaluateResponse(
        samples_count=result.samples_count,
        avg_faithfulness=result.avg_faithfulness,
        avg_relevancy=result.avg_relevancy,
        avg_context_precision=result.avg_context_precision,
        avg_context_recall=result.avg_context_recall,
        raw_scores=result.raw_scores,
        models=models,
    )


def _nonempty_contexts_from_sample(contexts: list[str] | None) -> list[str]:
    out: list[str] = []
    for c in contexts or []:
        t = str(c).strip()
        if t:
            out.append(t)
    return out


def _ragas_compare_corpus_text(contexts: list[str]) -> str:
    return "\n\n---\n\n".join(contexts)


def run_compare_rag_vs_no_rag(
    jsonl: str,
    top_k: int,
    *,
    rag_service: "RAGService",
    ingestion: "IngestionService",
    project_service: "ProjectService",
    sources: "SourceRepository",
    users: "UserRepository",
    eval_user_id: int,
) -> RagasCompareResponse:
    """
    Для каждой строки JSONL (question, ground_truth, непустые contexts):
    1) Временный проект → индексация текстов contexts → RAG (retrieval + LLM) → удаление проекта и данных;
    2) Тот же вопрос — прямой LLM без документов;
    3) RAGAS по обеим веткам относительно ground_truth.
    """
    from evaluation.ragas.dataset_builder import EvalSample
    from modules.projects.schemas import ProjectCreate
    from modules.rag.schemas import AskRAGRequest
    from modules.sources.models import SourceType

    models = build_ragas_models_metadata(include_no_rag_llm=True)
    models = {
        **models,
        "rag_compare_mode": "ephemeral_contexts",
        "rag_compare_user_id": str(eval_user_id),
        "rag_compare_top_k": str(top_k),
    }
    logger.info(
        "ragas-compare[jsonl-contexts] start: jsonl_chars=%d top_k=%d eval_user_id=%d",
        len(jsonl or ""),
        top_k,
        eval_user_id,
    )

    if not users.get_by_id(eval_user_id):
        return RagasCompareResponse(
            error=(
                f"Нет пользователя с id={eval_user_id} (владелец временных проектов сравнения). "
                "Создайте пользователя в БД или задайте RAGAS_COMPARE_USER_ID."
            ),
            models=models,
        )

    dataset, err = _load_samples_from_jsonl_string(jsonl)
    if err:
        return RagasCompareResponse(error=err, models=models)

    rows = [s for s in dataset if s.question.strip() and s.ground_truth.strip()]
    if not rows:
        return RagasCompareResponse(
            error="В каждой строке нужны непустые question и ground_truth (эталон для RAGAS).",
            models=models,
        )

    for s in rows:
        ctxs = _nonempty_contexts_from_sample(s.contexts)
        if not ctxs:
            return RagasCompareResponse(
                error=(
                    "Для сравнения в каждой строке JSONL нужен непустой список contexts — по ним строится "
                    "временный индекс для ветки с RAG. Поле answer не используется."
                ),
                models=models,
            )

    rag_samples: list[EvalSample] = []
    rag_raw_samples: list[EvalSample] = []
    per_sample_standard: list[IngestStageStats] = []
    per_sample_raw: list[IngestStageStats] = []

    def _early_error(msg: str) -> RagasCompareResponse:
        return RagasCompareResponse(
            error=msg,
            questions=[x.question for x in rag_samples],
            rag_answers=[x.answer or "" for x in rag_samples],
            rag_raw_answers=[x.answer or "" for x in rag_raw_samples],
            processing=CompareProcessingStats(
                standard=_aggregate("standard", per_sample_standard),
                raw=_aggregate("raw", per_sample_raw),
                per_sample_standard=per_sample_standard,
                per_sample_raw=per_sample_raw,
            ),
            models=models,
        )

    def _run_one(mode: str, ctxs: list[str], question: str) -> tuple[EvalSample | None, IngestStageStats | None, str | None]:
        """Создать ephemeral-проект, проиндексировать contexts, выполнить RAG, удалить проект.

        Возвращает (EvalSample, метрики, error). При ошибке — (None, None, msg).
        """
        ephemeral_id: int | None = None
        try:
            tag = uuid.uuid4().hex[:12]
            project = project_service.create(
                ProjectCreate(
                    user_id=eval_user_id,
                    name=f"ragas-cmp-{mode}-{tag}"[:255],
                    prompt=None,
                    settings={"ephemeral": True, "ragas_compare": True, "ingest_mode": mode},
                )
            )
            ephemeral_id = project.id
            source = sources.create(
                project_id=ephemeral_id,
                source_type=SourceType.WEB,
                title=f"RAGAS eval corpus ({mode})",
                uri="https://example.invalid/ragas-eval",
                external_id=None,
                settings={"ragas_inline": True, "ingest_mode": mode},
            )
            _, ingest_metrics = ingestion.ingest_source_with_metrics(
                source,
                raw_text=_ragas_compare_corpus_text(ctxs),
                mode=mode,  # type: ignore[arg-type]
            )
            stage_stats = _stats_from_ingest_metrics(ingest_metrics)
            try:
                resp = rag_service.ask(
                    AskRAGRequest(project_id=ephemeral_id, query=question, top_k=top_k),
                    skip_log=True,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                return None, stage_stats, detail
            rctx = [c.content for c in resp.context_chunks]
            if not rctx:
                rctx = [EMPTY_RETRIEVAL_CONTEXT]
            return (
                EvalSample(
                    question=question,
                    contexts=rctx,
                    ground_truth="",  # заполним извне
                    answer=resp.answer,
                ),
                stage_stats,
                None,
            )
        except Exception as exc:
            logger.exception("RAGAS compare (%s) row failed", mode)
            return None, None, str(exc)
        finally:
            if ephemeral_id is not None:
                try:
                    project_service.delete(ephemeral_id)
                except Exception:
                    logger.exception("Failed to delete ephemeral RAGAS compare project %s (mode=%s)", ephemeral_id, mode)

    for s in rows:
        ctxs = _nonempty_contexts_from_sample(s.contexts)

        std_sample, std_stats, std_err = _run_one("standard", ctxs, s.question)
        if std_err is not None or std_sample is None:
            return _early_error(
                f"Ошибка ветки RAG (standard, вопрос: {s.question[:120]!r}…): {std_err or 'без ответа'}"
            )
        std_sample.ground_truth = s.ground_truth
        rag_samples.append(std_sample)
        if std_stats is not None:
            per_sample_standard.append(std_stats)

        raw_sample, raw_stats, raw_err = _run_one("raw", ctxs, s.question)
        if raw_err is not None or raw_sample is None:
            return _early_error(
                f"Ошибка ветки RAG (raw, вопрос: {s.question[:120]!r}…): {raw_err or 'без ответа'}"
            )
        raw_sample.ground_truth = s.ground_truth
        rag_raw_samples.append(raw_sample)
        if raw_stats is not None:
            per_sample_raw.append(raw_stats)

    processing = CompareProcessingStats(
        standard=_aggregate("standard", per_sample_standard),
        raw=_aggregate("raw", per_sample_raw),
        per_sample_standard=per_sample_standard,
        per_sample_raw=per_sample_raw,
    )
    _log_compare_aggregate("jsonl-contexts/standard", processing.standard)
    _log_compare_aggregate("jsonl-contexts/raw", processing.raw)

    return _run_compare_core(rag_samples, rag_raw_samples, models=models, processing=processing)


def _validate_urls(urls: list[str]) -> tuple[list[str], str | None]:
    cleaned: list[str] = []
    for raw in urls or []:
        u = (raw or "").strip()
        if not u:
            continue
        if not (u.startswith("http://") or u.startswith("https://")):
            return [], f"Некорректный URL (нужна схема http/https): {u!r}"
        cleaned.append(u)
    if not cleaned:
        return [], "Не передано ни одного URL."
    return cleaned, None


def run_compare_urls(
    jsonl: str,
    *,
    urls: list[str],
    top_k: int,
    rag_service: "RAGService",
    ingestion: "IngestionService",
    project_service: "ProjectService",
    sources: "SourceRepository",
    users: "UserRepository",
    eval_user_id: int,
) -> RagasCompareResponse:
    """
    Сравнение RAGAS на «живых» URL.

    На каждый режим (standard/raw) поднимается один временный проект, в него индексируются ВСЕ url
    как отдельные WEB-источники (со всем стандартным конвейером скрапинга/очистки/чанкования/embeddings).
    Затем для всех вопросов из JSONL выполняется RAG по проекту.
    `processing.per_sample_*` = метрики по каждому URL (а не по вопросам).
    """
    from evaluation.ragas.dataset_builder import EvalSample
    from modules.projects.schemas import ProjectCreate
    from modules.rag.schemas import AskRAGRequest
    from modules.sources.models import SourceType

    models = build_ragas_models_metadata(include_no_rag_llm=True)
    models = {
        **models,
        "rag_compare_mode": "ephemeral_urls",
        "rag_compare_user_id": str(eval_user_id),
        "rag_compare_top_k": str(top_k),
        "rag_compare_urls_count": str(len(urls or [])),
    }
    logger.info(
        "ragas-compare[urls] start: urls=%d jsonl_chars=%d top_k=%d eval_user_id=%d",
        len(urls or []),
        len(jsonl or ""),
        top_k,
        eval_user_id,
    )

    if not users.get_by_id(eval_user_id):
        return RagasCompareResponse(
            error=(
                f"Нет пользователя с id={eval_user_id} (владелец временных проектов сравнения). "
                "Создайте пользователя в БД или задайте RAGAS_COMPARE_USER_ID."
            ),
            models=models,
        )

    cleaned_urls, url_err = _validate_urls(urls)
    if url_err:
        return RagasCompareResponse(error=url_err, models=models)

    dataset, err = _load_samples_from_jsonl_string(jsonl)
    if err:
        return RagasCompareResponse(error=err, models=models)

    rows = [s for s in dataset if s.question.strip() and s.ground_truth.strip()]
    if not rows:
        return RagasCompareResponse(
            error="В каждой строке нужны непустые question и ground_truth (эталон для RAGAS).",
            models=models,
        )

    standard_project_id: int | None = None
    raw_project_id: int | None = None

    per_sample_standard: list[IngestStageStats] = []
    per_sample_raw: list[IngestStageStats] = []
    rag_samples: list[EvalSample] = []
    rag_raw_samples: list[EvalSample] = []

    def _early_error(msg: str) -> RagasCompareResponse:
        return RagasCompareResponse(
            error=msg,
            questions=[x.question for x in rag_samples],
            rag_answers=[x.answer or "" for x in rag_samples],
            rag_raw_answers=[x.answer or "" for x in rag_raw_samples],
            processing=CompareProcessingStats(
                standard=_aggregate("standard", per_sample_standard),
                raw=_aggregate("raw", per_sample_raw),
                per_sample_standard=per_sample_standard,
                per_sample_raw=per_sample_raw,
            ),
            models=models,
        )

    def _build_project(mode: str) -> tuple[int | None, list[IngestStageStats], str | None]:
        ephemeral_id: int | None = None
        per_sample: list[IngestStageStats] = []
        try:
            tag = uuid.uuid4().hex[:12]
            project = project_service.create(
                ProjectCreate(
                    user_id=eval_user_id,
                    name=f"ragas-urls-{mode}-{tag}"[:255],
                    prompt=None,
                    settings={"ephemeral": True, "ragas_compare": True, "ingest_mode": mode, "from_urls": True},
                )
            )
            ephemeral_id = project.id
            for url in cleaned_urls:
                source = sources.create(
                    project_id=ephemeral_id,
                    source_type=SourceType.WEB,
                    title=f"URL eval ({mode}): {url[:200]}",
                    uri=url,
                    external_id=None,
                    settings={"ragas_eval_url": True, "ingest_mode": mode},
                )
                try:
                    _, ingest_metrics = ingestion.ingest_source_with_metrics(source, raw_text=None, mode=mode)  # type: ignore[arg-type]
                except Exception as exc:
                    logger.exception("URL ingest failed (%s): %s", mode, url)
                    return ephemeral_id, per_sample, f"Не удалось загрузить/проиндексировать URL «{url}»: {exc}"
                if ingest_metrics.chunks_count == 0:
                    return ephemeral_id, per_sample, (
                        f"С URL «{url}» не удалось извлечь текст (страница пустая, требует JS или закрыта). "
                        "Проверьте ссылку или добавьте другой источник."
                    )
                per_sample.append(_stats_from_ingest_metrics(ingest_metrics))
            return ephemeral_id, per_sample, None
        except Exception as exc:
            logger.exception("Failed to build ephemeral RAGAS URLs project (%s)", mode)
            return ephemeral_id, per_sample, f"Ошибка подготовки проекта ({mode}): {exc}"

    try:
        standard_project_id, per_sample_standard, std_err = _build_project("standard")
        if std_err is not None:
            return _early_error(std_err)
        raw_project_id, per_sample_raw, raw_err = _build_project("raw")
        if raw_err is not None:
            return _early_error(raw_err)

        for s in rows:
            try:
                std_resp = rag_service.ask(
                    AskRAGRequest(project_id=standard_project_id, query=s.question, top_k=top_k),
                    skip_log=True,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                return _early_error(
                    f"Ошибка ветки RAG (standard, вопрос: {s.question[:120]!r}…): {detail}"
                )
            std_ctx = [c.content for c in std_resp.context_chunks] or [EMPTY_RETRIEVAL_CONTEXT]
            rag_samples.append(
                EvalSample(
                    question=s.question,
                    contexts=std_ctx,
                    ground_truth=s.ground_truth,
                    answer=std_resp.answer,
                )
            )

            try:
                raw_resp = rag_service.ask(
                    AskRAGRequest(project_id=raw_project_id, query=s.question, top_k=top_k),
                    skip_log=True,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                return _early_error(
                    f"Ошибка ветки RAG (raw, вопрос: {s.question[:120]!r}…): {detail}"
                )
            raw_ctx = [c.content for c in raw_resp.context_chunks] or [EMPTY_RETRIEVAL_CONTEXT]
            rag_raw_samples.append(
                EvalSample(
                    question=s.question,
                    contexts=raw_ctx,
                    ground_truth=s.ground_truth,
                    answer=raw_resp.answer,
                )
            )
    finally:
        for pid in (standard_project_id, raw_project_id):
            if pid is not None:
                try:
                    project_service.delete(pid)
                except Exception:
                    logger.exception("Failed to delete ephemeral RAGAS URLs project %s", pid)

    processing = CompareProcessingStats(
        standard=_aggregate("standard", per_sample_standard),
        raw=_aggregate("raw", per_sample_raw),
        per_sample_standard=per_sample_standard,
        per_sample_raw=per_sample_raw,
    )
    _log_compare_aggregate("urls/standard", processing.standard)
    _log_compare_aggregate("urls/raw", processing.raw)

    return _run_compare_core(rag_samples, rag_raw_samples, models=models, processing=processing)
