from harness.retry_policy import decide_retry_action, sanitize_retry_payload


def test_retry_policy_recode_decision() -> None:
    assert decide_retry_action(retry_count=0, replan_count=0) == "re-code"


def test_retry_policy_replan_decision() -> None:
    assert decide_retry_action(retry_count=3, replan_count=0) == "re-plan"


def test_retry_policy_fail_decision() -> None:
    assert decide_retry_action(retry_count=3, replan_count=2) == "fail"
    assert decide_retry_action(retry_count=0, replan_count=0, fatal=True) == "fail"


def test_sanitize_retry_payload_strips_hidden_fields() -> None:
    assert sanitize_retry_payload(
        {
            "issues": ["a"],
            "suggestions": ["b"],
            "score": 80,
            "verdict": "re-code",
        }
    ) == {
        "issues": ["a"],
        "suggestions": ["b"],
    }
