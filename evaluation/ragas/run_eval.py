"""
CLI entry point for running RAGAS evaluation.

Usage:
    python -m evaluation.ragas.run_eval --dataset path/to/dataset.jsonl

JSONL format (one object per line):
    {"question": "...", "contexts": ["..."], "ground_truth": "...", "answer": "..."}

Requires OPENROUTER_API_KEY for LLM-as-judge metrics.
"""
import argparse
import json
import logging
import sys

from evaluation.ragas.dataset_builder import build_dataset_from_jsonl
from evaluation.ragas.evaluator import RagasEvaluator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on a JSONL dataset")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset file")
    parser.add_argument("--output", default=None, help="Path to save JSON results (optional)")
    args = parser.parse_args()

    logger.info("Loading dataset from %s", args.dataset)
    dataset = build_dataset_from_jsonl(args.dataset)
    logger.info("Loaded %d samples", len(dataset))

    evaluator = RagasEvaluator()
    result = evaluator.evaluate(dataset)

    print("\n" + "=" * 50)
    print("RAGAS Evaluation Results")
    print("=" * 50)
    print(f"  Samples:           {result.samples_count}")
    print(f"  Faithfulness:      {result.avg_faithfulness:.4f}")
    print(f"  Answer Relevancy:  {result.avg_relevancy:.4f}")
    print(f"  Context Precision: {result.avg_context_precision:.4f}")
    print(f"  Context Recall:    {result.avg_context_recall:.4f}")
    print("=" * 50)

    if args.output:
        output_data = {
            "samples_count": result.samples_count,
            "avg_faithfulness": result.avg_faithfulness,
            "avg_relevancy": result.avg_relevancy,
            "avg_context_precision": result.avg_context_precision,
            "avg_context_recall": result.avg_context_recall,
            "raw_scores": result.raw_scores,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info("Results saved to %s", args.output)


if __name__ == "__main__":
    main()
