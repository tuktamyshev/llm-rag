"""
Build RAGAS-compatible evaluation datasets from JSONL files.

Supports both the official ragas EvaluationDataset (ragas >= 0.2)
and a plain dataclass fallback.

JSONL line format:
{
  "question": "...",
  "contexts": ["...", "..."],
  "ground_truth": "...",
  "answer": "..."
}
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EvalSample:
    """Plain dataclass for a single evaluation sample."""
    question: str
    contexts: list[str]
    ground_truth: str
    answer: str | None = None


def build_dataset_from_jsonl(path: str | Path) -> list[EvalSample]:
    """Load a JSONL file into a list of EvalSample objects."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    dataset: list[EvalSample] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        dataset.append(
            EvalSample(
                question=str(data["question"]),
                contexts=[str(item) for item in data.get("contexts", [])],
                ground_truth=str(data["ground_truth"]),
                answer=str(data["answer"]) if data.get("answer") is not None else None,
            )
        )
    return dataset


def build_ragas_dataset(samples: list[EvalSample]):
    """
    Convert EvalSample list into an official ragas EvaluationDataset.
    Requires ragas >= 0.2.
    """
    from ragas import SingleTurnSample, EvaluationDataset

    ragas_samples = []
    for s in samples:
        if s.answer is None:
            continue
        ragas_samples.append(
            SingleTurnSample(
                user_input=s.question,
                retrieved_contexts=s.contexts,
                response=s.answer,
                reference=s.ground_truth,
            )
        )
    return EvaluationDataset(samples=ragas_samples)
