from __future__ import annotations

import json

from harness.reporting import build_report, main


def test_reporting_payload_formatting() -> None:
    payload = build_report("taskComplete", task="Task 1", ok=True, details={"score": 95})
    assert payload["event"] == "taskComplete"
    assert payload["task"] == "Task 1"
    assert payload["ok"] is True
    assert payload["details"]["score"] == 95


def test_reporting_cli_emits_json_payload(capsys) -> None:
    exit_code = main(["taskComplete"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {"event": "taskComplete"}
