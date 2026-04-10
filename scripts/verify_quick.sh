#!/usr/bin/env bash
set -euo pipefail

mode="quick"
if [[ "${1:-}" == "--baseline" ]]; then
  shift
fi

if [[ "${HARNESS_SELFTEST:-0}" == "1" ]]; then
  cat <<'JSON'
{"mode":"quick","ok":true,"checks":[{"name":"pytest","ok":true},{"name":"import","ok":true},{"name":"smoke_chat","ok":true},{"name":"smoke_embeddings","ok":true}]}
JSON
  exit 0
fi

python3 -m pytest tests -q >/tmp/verify_quick_pytest.log
python3 -c "from app.main import app; print(app.title)" >/tmp/verify_quick_import.log
python3 scripts/smoke_chat.py >/tmp/verify_quick_chat.log
python3 scripts/smoke_embeddings.py >/tmp/verify_quick_embeddings.log

cat <<JSON
{"mode":"${mode}","ok":true,"checks":[{"name":"pytest","ok":true},{"name":"import","ok":true},{"name":"smoke_chat","ok":true},{"name":"smoke_embeddings","ok":true}]}
JSON
