from __future__ import annotations

import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from modules.evaluation.schemas import RagasCompareResponse, RagasEvaluateResponse, RagasMetricSummary

if TYPE_CHECKING:
    from modules.ingestion.service import IngestionService
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


def _run_compare_core(
    rag_samples: list[Any],
    *,
    models: dict[str, str],
) -> RagasCompareResponse:
    """Общая часть: ответы LLM без документов (вариант без RAG), RAGAS на rag_samples и на no_rag_samples."""
    from evaluation.ragas.dataset_builder import EvalSample
    from evaluation.ragas.evaluator import RagasEvaluator
    from infrastructure.llm.openrouter import OpenRouterLLMClient

    questions, rag_answers = _compare_pair_lists(rag_samples)
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
            no_rag_answers=no_rag_answers,
            error=f"Ошибка RAGAS (ветка RAG): {exc}",
            models=models,
        )

    try:
        no_rag_result = evaluator.evaluate(no_rag_samples)
    except Exception as exc:
        logger.exception("RAGAS on no-RAG samples failed")
        return RagasCompareResponse(
            samples_count=len(rag_samples),
            questions=questions,
            rag_answers=rag_answers,
            rag=_result_to_summary(rag_result.samples_count, rag_result),
            no_rag_answers=no_rag_answers,
            error=f"Ошибка RAGAS (ветка без RAG): {exc}",
            models=models,
        )

    return RagasCompareResponse(
        samples_count=len(rag_samples),
        questions=questions,
        rag_answers=rag_answers,
        rag=_result_to_summary(rag_result.samples_count, rag_result),
        no_rag=_result_to_summary(no_rag_result.samples_count, no_rag_result),
        no_rag_answers=no_rag_answers,
        models=models,
    )


def run_ragas_from_jsonl(jsonl: str) -> RagasEvaluateResponse:
    models = build_ragas_models_metadata()
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
    for s in rows:
        ctxs = _nonempty_contexts_from_sample(s.contexts)
        ephemeral_id: int | None = None
        try:
            tag = uuid.uuid4().hex[:12]
            project = project_service.create(
                ProjectCreate(
                    user_id=eval_user_id,
                    name=f"ragas-cmp-{tag}"[:255],
                    prompt=None,
                    settings={"ephemeral": True, "ragas_compare": True},
                )
            )
            ephemeral_id = project.id
            source = sources.create(
                project_id=ephemeral_id,
                source_type=SourceType.WEB,
                title="RAGAS eval corpus",
                uri="https://example.invalid/ragas-eval",
                external_id=None,
                settings={"ragas_inline": True},
            )
            ingestion.ingest_source_now(source, raw_text=_ragas_compare_corpus_text(ctxs))
            try:
                resp = rag_service.ask(
                    AskRAGRequest(project_id=ephemeral_id, query=s.question, top_k=top_k),
                    skip_log=True,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                return RagasCompareResponse(
                    error=f"Ошибка ветки с RAG (вопрос: {s.question[:120]!r}…): {detail}",
                    questions=[x.question for x in rag_samples],
                    rag_answers=[x.answer or "" for x in rag_samples],
                    models=models,
                )
            rctx = [c.content for c in resp.context_chunks]
            if not rctx:
                rctx = [EMPTY_RETRIEVAL_CONTEXT]
            rag_samples.append(
                EvalSample(
                    question=s.question,
                    contexts=rctx,
                    ground_truth=s.ground_truth,
                    answer=resp.answer,
                )
            )
        except Exception as exc:
            logger.exception("RAGAS compare row failed")
            return RagasCompareResponse(
                error=f"Ошибка подготовки временного проекта или RAG: {exc}",
                questions=[x.question for x in rag_samples],
                rag_answers=[x.answer or "" for x in rag_samples],
                models=models,
            )
        finally:
            if ephemeral_id is not None:
                try:
                    project_service.delete(ephemeral_id)
                except Exception:
                    logger.exception("Failed to delete ephemeral RAGAS compare project %s", ephemeral_id)

    return _run_compare_core(rag_samples, models=models)
