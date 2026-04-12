from __future__ import annotations

from harness.checks.cross_llm import CrossLLMReviewResult, build_cross_llm_result, build_retry_payload


def test_retry_payload_excludes_hidden_score_fields() -> None:
    review = CrossLLMReviewResult(
        issues=["fix this"],
        suggestions=["do that"],
        verdict="re-code",
        score=71,
    )
    payload = build_retry_payload(review)

    assert payload == {
        "issues": ["fix this"],
        "suggestions": ["do that"],
    }


def test_cross_llm_result_builder_preserves_internal_review_fields() -> None:
    payload = build_cross_llm_result(
        issues=["fix this"],
        suggestions=["do that"],
        verdict="re-code",
        score=71,
    )

    assert payload == {
        "issues": ["fix this"],
        "suggestions": ["do that"],
        "verdict": "re-code",
        "score": 71,
    }


def test_cross_llm_result_shape_is_stable() -> None:
    review = CrossLLMReviewResult(
        issues=["a"],
        suggestions=["b"],
        verdict="pass",
        score=100,
    )

    assert review.issues == ["a"]
    assert review.suggestions == ["b"]
    assert review.verdict == "pass"
    assert review.score == 100
