from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CrossLLMReviewResult:
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    verdict: str = "pass"
    score: int = 100


def build_retry_payload(review: CrossLLMReviewResult) -> dict[str, Any]:
    return {
        "issues": review.issues,
        "suggestions": review.suggestions,
    }


def build_cross_llm_result(*, issues: list[str], suggestions: list[str], verdict: str, score: int) -> dict[str, Any]:
    return CrossLLMReviewResult(
        issues=issues,
        suggestions=suggestions,
        verdict=verdict,
        score=score,
    ).__dict__
