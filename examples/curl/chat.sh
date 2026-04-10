#!/usr/bin/env bash
set -euo pipefail

: "${PROXY_URL:=http://127.0.0.1:8080}"
: "${PROXY_TOKEN:=change-me}"
: "${MODEL:=google/gemini-2.5-flash}"

curl -sS \
  -X POST "${PROXY_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${PROXY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"You are a helpful assistant.\"},
      {\"role\": \"user\", \"content\": \"Say hello in one short sentence.\"}
    ]
  }"
