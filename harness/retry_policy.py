from __future__ import annotations

from typing import Any


def decide_retry_action(*, retry_count: int, replan_count: int, fatal: bool = False) -> str:
    if fatal:
        return "fail"
    if retry_count < 3:
        return "re-code"
    if replan_count < 2:
        return "re-plan"
    return "fail"


def sanitize_retry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"score", "verdict"}
    }


def main() -> int:
    return 0
