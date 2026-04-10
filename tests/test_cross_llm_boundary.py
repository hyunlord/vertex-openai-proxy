from __future__ import annotations

import json
from pathlib import Path

from harness.checks.cross_llm import CrossLLMReviewResult, build_retry_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def test_config_represents_coder_verifier_separation() -> None:
    config = json.loads((PROJECT_ROOT / ".vertex-proxy/config.json").read_text())
    models = config["agent_models"]

    assert models["coder"] != models["verifier"]


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
