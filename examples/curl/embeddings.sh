#!/usr/bin/env bash
set -euo pipefail

: "${PROXY_URL:=http://127.0.0.1:8080}"
: "${PROXY_TOKEN:=change-me}"
: "${MODEL:=gemini-embedding-2-preview}"

curl -sS \
  -X POST "${PROXY_URL}/v1/embeddings" \
  -H "Authorization: Bearer ${PROXY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"input\": [\"first text\", \"second text\"]
  }"
