from __future__ import annotations

import os
from typing import Any


def deepeval_enabled() -> bool:
    return os.getenv("ENABLE_DEEPEVAL", "0") == "1"


def evaluate_with_deepeval(question: str, answer: str, context: list[str], expected_answer: str | None = None) -> list[dict[str, Any]]:
    """Optional LLM-based semantic checks.

    The offline evaluator never calls this unless ENABLE_DEEPEVAL=1. DeepEval metrics
    may require an LLM provider configured by the user. These results supplement,
    never replace, deterministic contract/security checks.
    """
    if not deepeval_enabled():
        return [{
            "rule": "deepeval_optional_metrics",
            "expected": "ENABLE_DEEPEVAL=1 and a configured DeepEval-compatible model/provider",
            "observed": "disabled",
            "verdict": "NOT_EVALUATED",
            "reason": "Optional LLM-based evaluation is disabled; offline deterministic evaluation remains complete.",
        }]

    try:
        from deepeval.test_case import LLMTestCase
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ContextualRelevancyMetric, GEval
        from deepeval.test_case import LLMTestCaseParams
    except Exception as exc:  # pragma: no cover - optional dependency path
        return [{
            "rule": "deepeval_optional_metrics",
            "expected": "DeepEval importable",
            "observed": repr(exc),
            "verdict": "NOT_EVALUATED",
            "reason": "DeepEval is not available in this environment.",
        }]

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        expected_output=expected_answer,
        retrieval_context=context,
    )
    metrics = [
        AnswerRelevancyMetric(threshold=0.7),
        FaithfulnessMetric(threshold=0.7),
        ContextualRelevancyMetric(threshold=0.7),
    ]
    if expected_answer:
        metrics.append(GEval(
            name="Semantic Equivalence",
            criteria="Determine whether the actual output preserves the required policy meaning of the expected output without introducing unsupported claims.",
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
            threshold=0.7,
        ))

    results = []
    for metric in metrics:  # pragma: no cover - optional live LLM path
        try:
            metric.measure(test_case)
            score = getattr(metric, "score", None)
            threshold = getattr(metric, "threshold", 0.7)
            results.append({
                "rule": f"deepeval_{metric.__class__.__name__}",
                "expected": f"score >= {threshold}",
                "observed": score,
                "verdict": "PASS" if score is not None and score >= threshold else "FAIL",
                "reason": getattr(metric, "reason", "DeepEval metric result."),
            })
        except Exception as exc:
            results.append({
                "rule": f"deepeval_{metric.__class__.__name__}",
                "expected": "metric executes",
                "observed": repr(exc),
                "verdict": "NOT_EVALUATED",
                "reason": "Optional DeepEval metric could not be executed.",
            })
    return results
