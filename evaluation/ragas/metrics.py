import re

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Lightweight proxy metric:
    share of answer tokens that are supported by retrieved contexts.
    """
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    context_tokens: set[str] = set()
    for chunk in contexts:
        context_tokens |= _tokenize(chunk)
    overlap = answer_tokens & context_tokens
    return len(overlap) / len(answer_tokens)


def relevancy(answer: str, question: str) -> float:
    """
    Lightweight proxy metric:
    overlap between question tokens and answer tokens.
    """
    answer_tokens = _tokenize(answer)
    question_tokens = _tokenize(question)
    if not question_tokens:
        return 0.0
    overlap = answer_tokens & question_tokens
    return len(overlap) / len(question_tokens)


def context_precision(contexts: list[str], ground_truth: str) -> float:
    """
    Proxy precision:
    share of context tokens that are relevant to the ground truth.
    """
    context_tokens: set[str] = set()
    for chunk in contexts:
        context_tokens |= _tokenize(chunk)
    if not context_tokens:
        return 0.0
    truth_tokens = _tokenize(ground_truth)
    overlap = context_tokens & truth_tokens
    return len(overlap) / len(context_tokens)


def context_recall(contexts: list[str], ground_truth: str) -> float:
    """
    Proxy recall:
    share of ground-truth tokens covered by retrieved contexts.
    """
    truth_tokens = _tokenize(ground_truth)
    if not truth_tokens:
        return 0.0
    context_tokens: set[str] = set()
    for chunk in contexts:
        context_tokens |= _tokenize(chunk)
    overlap = context_tokens & truth_tokens
    return len(overlap) / len(truth_tokens)
