"""
RAGAS evaluation metrics using the official `ragas` library (v0.4+).

Provides LLM-based evaluation of RAG quality with four core metrics:
- Faithfulness: are all claims in the answer supported by the context?
- Answer Relevancy: how relevant is the answer to the question?
- Context Precision: how many retrieved chunks are actually useful?
- Context Recall: was all necessary information retrieved?

Requires: pip install ragas langchain-openai
LLM judge is configured via OPENROUTER_API_KEY / OPENROUTER_MODEL.
"""
from __future__ import annotations

import logging
import os
import warnings

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")


def _get_ragas_llm():
    """Build a ragas-compatible LLM wrapper backed by OpenRouter."""
    try:
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set — LLM-based RAGAS metrics unavailable")
            return None

        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0,
        )
        return LangchainLLMWrapper(llm)
    except Exception as exc:
        logger.warning("Failed to create RAGAS LLM: %s", exc)
        return None


def _get_ragas_embeddings():
    """Build ragas-compatible embeddings using LangChain + sentence-transformers."""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper

        model_name = os.getenv("RAGAS_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        lc_embeddings = HuggingFaceEmbeddings(model_name=model_name)
        return LangchainEmbeddingsWrapper(lc_embeddings)
    except Exception as exc:
        logger.warning("Could not load embeddings for RAGAS: %s", exc)
        return None


def get_ragas_metrics():
    """
    Return a list of configured RAGAS metric instances compatible with ragas.evaluate().
    Uses the legacy metric classes that implement ragas.metrics.base.Metric.
    """
    try:
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )

        llm = _get_ragas_llm()
        embeddings = _get_ragas_embeddings()

        if llm is not None:
            faithfulness.llm = llm
            answer_relevancy.llm = llm
            context_precision.llm = llm
            context_recall.llm = llm

        if embeddings is not None:
            answer_relevancy.embeddings = embeddings

        return [faithfulness, answer_relevancy, context_precision, context_recall]
    except ImportError as exc:
        logger.error("ragas library not installed: %s", exc)
        raise
