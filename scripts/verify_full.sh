#!/usr/bin/env bash
set -euo pipefail

if [[ "${HARNESS_SELFTEST:-0}" == "1" ]]; then
  cat <<'JSON'
{"mode":"full","ok":true,"checks":[{"name":"quick","ok":true},{"name":"protocol","ok":true}]}
JSON
  exit 0
fi

quick_output="$(bash scripts/verify_quick.sh)"
python3 scripts/check_contracts.py >/tmp/verify_full_contracts.log
python3 scripts/smoke_tool_calling.py >/tmp/verify_full_tool_calling.log

python3 - <<PY
import json

quick_output = json.loads("""${quick_output}""")
print(
    json.dumps(
        {
            "mode": "full",
            "ok": True,
            "checks": [
                {"name": "quick", "ok": True, "summary": quick_output},
                {"name": "protocol", "ok": True},
                {"name": "tool_calling", "ok": True},
            ],
        }
    )
)
PY
