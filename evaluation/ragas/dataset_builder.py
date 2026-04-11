import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EvalSample:
    question: str
    contexts: list[str]
    ground_truth: str
    answer: str | None = None


def build_dataset_from_jsonl(path: str | Path) -> list[EvalSample]:
    """
    JSONL line format:
    {
      "question": "...",
      "contexts": ["...", "..."],
      "ground_truth": "...",
      "answer": "..."  # optional
    }
    """
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
