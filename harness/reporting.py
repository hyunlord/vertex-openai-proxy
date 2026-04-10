from __future__ import annotations

import json
import sys
from typing import Any


def build_report(event: str, *, task: str | None = None, ok: bool | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"event": event}
    if task is not None:
        payload["task"] = task
    if ok is not None:
        payload["ok"] = ok
    if details is not None:
        payload["details"] = details
    return payload


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    event = args[0] if args else "report"
    print(json.dumps(build_report(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
