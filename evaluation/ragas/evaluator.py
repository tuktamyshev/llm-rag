from dataclasses import dataclass

from evaluation.ragas.dataset_builder import EvalSample
from evaluation.ragas.metrics import context_precision, context_recall, faithfulness, relevancy


@dataclass(slots=True)
class EvaluationResult:
    samples_count: int
    avg_faithfulness: float
    avg_relevancy: float
    avg_context_precision: float
    avg_context_recall: float


class RagasEvaluator:
    """
    Offline evaluator. It does not integrate with runtime API.
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

        faithfulness_scores: list[float] = []
        relevancy_scores: list[float] = []
        precision_scores: list[float] = []
        recall_scores: list[float] = []

        for sample in dataset:
            if sample.answer is None:
                raise ValueError("Each sample must include 'answer' for evaluation")

            faithfulness_scores.append(faithfulness(sample.answer, sample.contexts))
            relevancy_scores.append(relevancy(sample.answer, sample.question))
            precision_scores.append(context_precision(sample.contexts, sample.ground_truth))
            recall_scores.append(context_recall(sample.contexts, sample.ground_truth))

        count = len(dataset)
        return EvaluationResult(
            samples_count=count,
            avg_faithfulness=sum(faithfulness_scores) / count,
            avg_relevancy=sum(relevancy_scores) / count,
            avg_context_precision=sum(precision_scores) / count,
            avg_context_recall=sum(recall_scores) / count,
        )
