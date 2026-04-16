# Configuration

This document separates the small set of settings most users need from the advanced knobs used for production tuning.

## Core Settings

These are the settings most deployments should care about first:

- `INTERNAL_BEARER_TOKEN`
  - shared secret that callers present to this proxy
- `VERTEX_PROJECT_ID`
  - Google Cloud project ID for Vertex AI calls
- `VERTEX_CHAT_LOCATION`
  - chat endpoint region such as `global`
- `VERTEX_EMBEDDING_LOCATION`
  - embedding endpoint region such as `us-central1`
- `VERTEX_CHAT_MODEL`
  - default chat model ID
- `VERTEX_CHAT_MODELS`
  - optional comma-separated extra chat model IDs
- `VERTEX_CHAT_MODEL_ALIASES`
  - optional comma-separated `alias=model-id` pairs
- `VERTEX_EMBEDDING_MODEL`
  - default embedding model ID
- `REQUEST_TIMEOUT_SECONDS`
  - upstream request timeout
- `VERTEX_ACCESS_TOKEN`
  - optional local debugging override instead of ADC / Workload Identity

Example:

```env
INTERNAL_BEARER_TOKEN=replace-with-a-random-token
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_CHAT_LOCATION=global
VERTEX_EMBEDDING_LOCATION=us-central1
VERTEX_CHAT_MODEL=google/gemini-2.5-flash
VERTEX_CHAT_MODELS=
VERTEX_CHAT_MODEL_ALIASES=
VERTEX_EMBEDDING_MODEL=gemini-embedding-2-preview
REQUEST_TIMEOUT_SECONDS=60
```

## Advanced Runtime Settings

These settings are useful when you are tuning a real deployment and need to shape queueing, admission control, retries, or adaptive behavior.

### Embedding Fan-Out And Retry

- `EMBEDDING_MAX_CONCURRENCY`
- `EMBEDDING_MAX_INPUTS_PER_REQUEST`
- `EMBEDDING_RETRY_ATTEMPTS`
- `EMBEDDING_RETRY_BACKOFF_MS`

### Embedding Adaptive Concurrency

- `EMBEDDING_ADAPTIVE_CONCURRENCY`
- `EMBEDDING_ADAPTIVE_MAX_CONCURRENCY`
- `EMBEDDING_ADAPTIVE_WINDOW_SIZE`
- `EMBEDDING_ADAPTIVE_WINDOW_SECONDS`
- `EMBEDDING_ADAPTIVE_COOLDOWN_SECONDS`
- `EMBEDDING_ADAPTIVE_MIN_SAMPLES`
- `EMBEDDING_ADAPTIVE_LATENCY_UP_THRESHOLD_MS`
- `EMBEDDING_ADAPTIVE_LATENCY_DOWN_THRESHOLD_MS`
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_UP_THRESHOLD`
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_DOWN_THRESHOLD`

### Shared Runtime Mode

- `RUNTIME_ADAPTIVE_MODE`
- `READINESS_FAIL_ON_DEGRADED`
- `RUNTIME_WINDOW_SIZE`
- `RUNTIME_WINDOW_SECONDS`
- `RUNTIME_RECOVERY_SECONDS`
- `RUNTIME_SOFT_IN_FLIGHT_CHAT`
- `RUNTIME_HARD_IN_FLIGHT_CHAT`
- `RUNTIME_SOFT_IN_FLIGHT_EMBEDDINGS`
- `RUNTIME_HARD_IN_FLIGHT_EMBEDDINGS`
- `CHAT_MAX_IN_FLIGHT_REQUESTS`
- `EMBEDDINGS_MAX_IN_FLIGHT_REQUESTS`
- `RUNTIME_DEGRADED_CHAT_MAX_IN_FLIGHT`
- `RUNTIME_DEGRADED_EMBEDDINGS_MAX_IN_FLIGHT`
- `RUNTIME_DEGRADED_MAX_EMBEDDING_INPUTS`
- `RUNTIME_CHAT_SOFT_LATENCY_MS`
- `RUNTIME_CHAT_HARD_LATENCY_MS`
- `RUNTIME_EMBEDDINGS_SOFT_LATENCY_MS`
- `RUNTIME_EMBEDDINGS_HARD_LATENCY_MS`
- `RUNTIME_SOFT_RETRYABLE_ERROR_RATE`
- `RUNTIME_HARD_RETRYABLE_ERROR_RATE`
- `RUNTIME_SOFT_TIMEOUT_RATE`
- `RUNTIME_HARD_TIMEOUT_RATE`
- `RUNTIME_HARD_CPU_PERCENT`
- `RUNTIME_HARD_RSS_MB`

### Queueing

- `QUEUE_ENABLED`
- `QUEUE_DISABLE_ON_DEGRADED`
- `QUEUE_POLL_INTERVAL_MS`
- `QUEUE_RETRY_AFTER_SECONDS`
- `CHAT_QUEUE_MAX_WAIT_MS`
- `CHAT_QUEUE_MAX_DEPTH`
- `EMBEDDINGS_QUEUE_MAX_WAIT_MS`
- `EMBEDDINGS_QUEUE_MAX_DEPTH`

### Chat Retry

- `CHAT_RETRY_ATTEMPTS`
- `CHAT_RETRY_BACKOFF_MS`

## Full Example File

The current full environment template lives in:

```bash
cat .env.example
```

That file is the source of truth for every supported environment variable.
