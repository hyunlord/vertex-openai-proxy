from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_scripts_exist_and_are_executable() -> None:
    for relative_path in [
        "scripts/verify_quick.sh",
        "scripts/verify_full.sh",
        "scripts/smoke_chat.py",
        "scripts/smoke_embeddings.py",
        "scripts/smoke_tool_calling.py",
        "scripts/smoke_vm_direct.py",
        "scripts/smoke_in_cluster.py",
    ]:
        path = PROJECT_ROOT / relative_path
        assert path.exists()
        if path.suffix == ".sh":
            mode = path.stat().st_mode
            assert mode & stat.S_IXUSR


def test_verify_scripts_return_structured_json_in_selftest_mode() -> None:
    env = {**os.environ, "HARNESS_SELFTEST": "1"}

    quick = subprocess.run(
        ["bash", "scripts/verify_quick.sh"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    full = subprocess.run(
        ["bash", "scripts/verify_full.sh"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    quick_payload = json.loads(quick.stdout)
    full_payload = json.loads(full.stdout)

    assert quick_payload["mode"] == "quick"
    assert quick_payload["ok"] is True
    assert full_payload["mode"] == "full"
    assert full_payload["ok"] is True
