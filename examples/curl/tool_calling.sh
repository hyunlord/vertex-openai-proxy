#!/usr/bin/env bash
set -euo pipefail

: "${PROXY_URL:=http://127.0.0.1:8080}"
: "${PROXY_TOKEN:=replace-with-a-random-token}"
: "${MODEL:=google/gemini-2.5-flash}"

curl -sS \
  -X POST "${PROXY_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${PROXY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"You are a careful assistant.\"},
      {\"role\": \"user\", \"content\": \"What is the weather in Seoul? Use the provided tool if needed.\"}
    ],
    \"tools\": [
      {
        \"type\": \"function\",
        \"function\": {
          \"name\": \"get_weather\",
          \"description\": \"Get the current weather for a city.\"
        }
      }
    ],
    \"tool_choice\": \"auto\"
  }"
