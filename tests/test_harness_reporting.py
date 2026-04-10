from __future__ import annotations

import json
from pathlib import Path

from harness.reporting import build_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_hooks_config_has_expected_shape() -> None:
    hooks = json.loads((PROJECT_ROOT / ".vertex-proxy/hooks.json").read_text())
    for key in ["taskStart", "postCode", "postVerify", "taskComplete", "taskFail"]:
        assert key in hooks
        assert isinstance(hooks[key], list)


def test_reporting_payload_formatting() -> None:
    payload = build_report("taskComplete", task="Task 1", ok=True, details={"score": 95})
    assert payload["event"] == "taskComplete"
    assert payload["task"] == "Task 1"
    assert payload["ok"] is True
    assert payload["details"]["score"] == 95
