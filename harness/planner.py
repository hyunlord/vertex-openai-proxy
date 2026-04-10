from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    phase = args[0] if args else "plan"
    print(json.dumps({"event": phase, "ok": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
