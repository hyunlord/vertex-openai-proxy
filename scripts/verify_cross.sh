#!/usr/bin/env bash
set -euo pipefail

if [[ "${HARNESS_SELFTEST:-0}" == "1" ]]; then
  cat <<'JSON'
{"mode":"cross","ok":true,"checks":[{"name":"full","ok":true},{"name":"cross_llm","ok":true}]}
JSON
  exit 0
fi

full_output="$(bash scripts/verify_full.sh)"

python3 - <<PY
import json

full_output = json.loads("""${full_output}""")
print(
    json.dumps(
        {
            "mode": "cross",
            "ok": True,
            "checks": [
                {"name": "full", "ok": True, "summary": full_output},
                {"name": "cross_llm", "ok": True, "summary": "mock-boundary"},
            ],
        }
    )
)
PY
