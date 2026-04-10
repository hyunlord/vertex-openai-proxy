from __future__ import annotations

import subprocess
from time import perf_counter

from harness.types import CheckResult


def run_mechanical_check(name: str, command: list[str], *, cwd: str | None = None) -> CheckResult:
    started_at = perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
    summary = format_command_summary(completed.returncode, completed.stdout, completed.stderr, elapsed_ms)
    return CheckResult(name=name, passed=completed.returncode == 0, summary=summary)


def format_command_summary(
    exit_code: int,
    stdout: str,
    stderr: str,
    elapsed_ms: float,
) -> str:
    stdout_preview = stdout.strip().splitlines()[:3]
    stderr_preview = stderr.strip().splitlines()[:3]
    return (
        f"exit_code={exit_code} elapsed_ms={elapsed_ms} "
        f"stdout={stdout_preview} stderr={stderr_preview}"
    )
