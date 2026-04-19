"""
RAG evaluator using the official ragas library.

Runs ragas.evaluate() with Faithfulness, AnswerRelevancy,
ContextPrecision, and ContextRecall metrics.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from evaluation.ragas.dataset_builder import EvalSample, build_ragas_dataset
from evaluation.ragas.metrics import get_ragas_metrics

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EvaluationResult:
    samples_count: int
    avg_faithfulness: float
    avg_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    raw_scores: dict | None = None


class RagasEvaluator:
    """
    Evaluator that delegates scoring to the official ragas library.
    Uses LLM-as-judge for all four core metrics.
    """

    def evaluate(self, dataset: list[EvalSample]) -> EvaluationResult:
        if not dataset:
            return EvaluationResult(
                samples_count=0,
                avg_faithfulness=0.0,
                avg_relevancy=0.0,
                avg_context_precision=0.0,
                avg_context_recall=0.0,
            )

        samples_with_answers = [s for s in dataset if s.answer is not None]
        if not samples_with_answers:
            raise ValueError("No samples with answers found in dataset")

        ragas_dataset = build_ragas_dataset(samples_with_answers)
        metrics = get_ragas_metrics()

        from ragas import evaluate as ragas_evaluate

        logger.info(
            "Running RAGAS evaluation on %d samples with %d metrics...",
            len(samples_with_answers),
            len(metrics),
        )

        result = ragas_evaluate(
            dataset=ragas_dataset,
            metrics=metrics,
        )

        scores = result.to_pandas()
        raw = {}

        faithfulness_score = 0.0
        relevancy_score = 0.0
        precision_score = 0.0
        recall_score = 0.0

        if "faithfulness" in scores.columns:
            faithfulness_score = scores["faithfulness"].mean()
            raw["faithfulness"] = scores["faithfulness"].tolist()

        if "answer_relevancy" in scores.columns:
            relevancy_score = scores["answer_relevancy"].mean()
            raw["answer_relevancy"] = scores["answer_relevancy"].tolist()

        precision_col = next(
            (c for c in scores.columns if "context_precision" in c), None,
        )
        if precision_col:
            precision_score = scores[precision_col].mean()
            raw["context_precision"] = scores[precision_col].tolist()

        if "context_recall" in scores.columns:
            recall_score = scores["context_recall"].mean()
            raw["context_recall"] = scores["context_recall"].tolist()

        return EvaluationResult(
            samples_count=len(samples_with_answers),
            avg_faithfulness=float(faithfulness_score),
            avg_relevancy=float(relevancy_score),
            avg_context_precision=float(precision_score),
            avg_context_recall=float(recall_score),
            raw_scores=raw,
        )
