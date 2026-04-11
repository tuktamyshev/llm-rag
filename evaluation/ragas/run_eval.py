import argparse

from evaluation.ragas.dataset_builder import build_dataset_from_jsonl
from evaluation.ragas.evaluator import RagasEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline RAGAS-like evaluation")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset file")
    args = parser.parse_args()

    dataset = build_dataset_from_jsonl(args.dataset)
    result = RagasEvaluator().evaluate(dataset)

    print("Evaluation finished")
    print(f"Samples:      {result.samples_count}")
    print(f"Faithfulness: {result.avg_faithfulness:.4f}")
    print(f"Relevancy:    {result.avg_relevancy:.4f}")
    print(f"Ctx Precision:{result.avg_context_precision:.4f}")
    print(f"Ctx Recall:   {result.avg_context_recall:.4f}")


if __name__ == "__main__":
    main()
