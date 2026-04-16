# vertex-openai-proxy

Reference OpenAI-compatible proxy for Vertex AI on GKE.

This service accepts a focused OpenAI-compatible API surface and forwards requests to Vertex AI using Workload Identity, ADC, or metadata-based access tokens. It is designed as a narrow, predictable compatibility layer rather than a multi-provider gateway.

## Start Here

- first-time setup and local bring-up: [docs/quickstart.md](docs/quickstart.md)
- configuration reference and advanced knobs: [docs/configuration.md](docs/configuration.md)
- validation paths for local, VM, and in-cluster checks: [docs/validation.md](docs/validation.md)
- operator rollout and rollback guidance: [docs/runbook.md](docs/runbook.md)
- GenOS / GKE transition guidance: [docs/operations-transition.md](docs/operations-transition.md)

## Project Priorities

This repository is maintained in this order:

1. keep the project legally and operationally usable as public open source
2. keep the real GKE / GenOS serving path stable
3. expand compatibility and operator features without widening scope too fast

## Why This Exists

Some clients expect:
- an OpenAI-compatible base URL
- a fixed bearer token

Vertex AI on GKE works best with Workload Identity and short-lived Google access tokens, not a long-lived static API key. This proxy bridges that gap by:
- validating one internal static bearer token from the client
- minting Vertex access tokens from GKE metadata/ADC
- forwarding requests to Vertex AI
- normalizing chat and embedding responses into stable OpenAI-style shapes

## Supported Endpoints

- `GET /health`
- `GET /livez`
- `GET /readyz`
- `GET /runtimez`
- `GET /metrics`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`

## Supported Compatibility Surface

- `chat.completions`
  - non-streaming JSON responses
  - streaming SSE responses with `chat.completion.chunk`
- `embeddings`
  - single-string input
  - list input with explicit fan-out and ordered merge
- normalized OpenAI-style error envelopes
- model allowlist via `/v1/models`

## Current Limitations

- no multi-provider routing
- no caching or rate limiting
- no Responses API or Assistants API
- no image/audio content-parts support yet
- no multimodal content-parts normalization yet
- embeddings intentionally fail the entire request if any item fails

See [architecture](docs/architecture.md), [compatibility](docs/compatibility.md), [troubleshooting](docs/troubleshooting.md), and [roadmap](docs/roadmap.md) for details.

For real-world tuning and model behavior history, see the running [empirical testing log](docs/empirical-testing.md). Future live model tests should be appended there instead of being kept only in ad-hoc notes.

Release history is tracked in [CHANGELOG.md](CHANGELOG.md).
Security reporting guidance lives in [SECURITY.md](SECURITY.md).
Community expectations live in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

For private infrastructure handoff guidance, see [docs/private-handoff.md](docs/private-handoff.md).
For canary rollout guidance, see [docs/canary-checklist.md](docs/canary-checklist.md).

## Runtime Policy

This proxy prefers correctness over speculative batching.

- embeddings always normalize list input into one upstream call per input item
- embeddings preserve input order and return one vector per item
- embeddings use bounded fan-out concurrency instead of implicit true batch behavior
- embeddings fail the whole request if any item fails
- embeddings `usage` is an approximate split-based estimate when Vertex does not provide tokenizer counts
- non-stream chat uses conservative retries for retry-safe upstream failures
- stream chat avoids retries after a stream starts to prevent ambiguous partial output

The runtime knobs are conservative by default so the proxy remains predictable under array inputs and moderate concurrency.

## Environment Variables

Start by copying the example file:

```bash
cp .env.example .env
```

Core settings for most users:

- `INTERNAL_BEARER_TOKEN`: Shared secret used by the client when calling this proxy
- `VERTEX_PROJECT_ID`: Google Cloud project ID
- `VERTEX_CHAT_LOCATION`: Chat endpoint location such as `global`
- `VERTEX_EMBEDDING_LOCATION`: Embedding endpoint location such as `us-central1`
- `VERTEX_CHAT_MODEL`: Default chat model ID
- `VERTEX_CHAT_MODELS`: Optional comma-separated extra chat model IDs
- `VERTEX_CHAT_MODEL_ALIASES`: Optional comma-separated `alias=model-id` pairs
- `VERTEX_EMBEDDING_MODEL`: Default embedding model ID
- `REQUEST_TIMEOUT_SECONDS`: Upstream timeout

Advanced runtime, queue, retry, and adaptive knobs are documented in [docs/configuration.md](docs/configuration.md).

## Runtime Health And Metrics

The proxy now exposes service-wide runtime state for both humans and automation:

- `/health`
  - compatibility endpoint with a summarized runtime payload
- `/livez`
  - process liveness only
- `/readyz`
  - readiness decision that can optionally fail on degraded mode
- `/runtimez`
  - detailed runtime snapshot including reasons, recent pressure, effective limits, and mode transitions
- `/metrics`
  - exposes Prometheus-friendly gauges for runtime mode, request health, retries, in-flight counts, adaptive embedding concurrency, and process pressure

## Overload Protection

When service-wide runtime adaptation is enabled, the proxy can protect itself with admission control instead of accepting work until latency collapses.

- absolute in-flight caps are always enforced for chat and embeddings
- degraded mode can apply tighter in-flight caps
- degraded mode can reject oversized embeddings batches early
- shed requests return `429` and are counted in `vertex_proxy_request_shed_total`

Optional bounded queueing is also available for short burst smoothing:

- queueing is disabled by default
- wait budgets stay intentionally short
- queue depth stays intentionally small
- degraded mode can disable queueing entirely
- queued requests that exceed their wait budget return `429`

This keeps the service explainable under pressure:
- `/readyz` can fail when `READINESS_FAIL_ON_DEGRADED=true`
- `/runtimez` shows current mode, reasons, and shed counters
- `/metrics` shows request shedding and mode transitions over time

Service-wide runtime mode is:

- `normal`
- `elevated`
- `degraded`

When `RUNTIME_ADAPTIVE_MODE=true`, chat and embeddings can react conservatively to that mode while
still preserving request correctness semantics.

## Verification Paths

This repository supports three validation paths:
- `mock/local`: unit, contract, and harness checks without a live Vertex dependency
- `vm direct`: run the proxy on a VM that already has working Vertex access and verify real chat and embeddings flows end-to-end
- `in-cluster`: compare behavior inside GKE when Workload Identity and perimeter policy are expected to work

If GKE is blocked by VPC Service Controls or org policy, use `vm direct` to prove the proxy implementation still works independently of cluster policy.

## Example Client Configuration

- `API Format`: `OpenAI API`
- `API URL`: `http://your-proxy-host:8080`
- `Model`: `google/gemini-2.5-flash` for chat, `gemini-embedding-2-preview` for embeddings
- `Bearer Token`: value of `INTERNAL_BEARER_TOKEN`

## Multi-Chat-Model Configuration

One proxy instance can now expose multiple chat models while keeping embeddings on a single configured embedding model.

Example:

```env
VERTEX_CHAT_MODEL=google/gemini-3.1-flash-lite-preview
VERTEX_CHAT_MODELS=google/gemini-3.1-pro-preview
VERTEX_CHAT_MODEL_ALIASES=genos-flash=google/gemini-3.1-flash-lite-preview,genos-pro=google/gemini-3.1-pro-preview
VERTEX_EMBEDDING_MODEL=gemini-embedding-2-preview
```

With this configuration:
- callers may send `model=genos-flash`
- callers may send `model=genos-pro`
- callers may also send the raw Vertex chat model IDs directly
- embeddings remain single-model for now

## Quick Start Summary

If you are starting from scratch, use [docs/quickstart.md](docs/quickstart.md) first. The summary below is kept here as a fast reference.

1. Install dependencies for local development and verification:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Export configuration:
```bash
cp .env.example .env
export INTERNAL_BEARER_TOKEN=replace-with-a-random-token
export VERTEX_PROJECT_ID=your-gcp-project-id
export VERTEX_CHAT_LOCATION=global
export VERTEX_EMBEDDING_LOCATION=us-central1
```

3. Run the server:
```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

4. Verify:
```bash
curl -s http://127.0.0.1:8080/health
python3 -m pytest tests -q
```

For a runtime-only installation, use `pip install -r requirements.txt`.

## Validation And GKE Notes

For full validation paths and GKE-specific notes, see [docs/validation.md](docs/validation.md).

## Examples

- [curl chat example](examples/curl/chat.sh)
- [curl tool-calling example](examples/curl/tool_calling.sh)
- [curl embeddings example](examples/curl/embeddings.sh)
- [Python chat example](examples/python/chat.py)
- [Python tool-calling example](examples/python/tool_calling.py)

## Helm

This repository includes a generic Helm chart at [`charts/vertex-openai-proxy/`](charts/vertex-openai-proxy).

Basic install:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set image.repository=your-registry/vertex-openai-proxy \
  --set image.tag=latest \
  --set auth.internalBearerToken=replace-with-a-random-token \
  --set config.vertexProjectId=your-gcp-project-id
```

Using an existing secret:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set auth.existingSecret=vertex-openai-proxy-auth \
  --set auth.existingSecretKey=internal-bearer-token
```

The chart fails closed if neither `auth.existingSecret` nor `auth.internalBearerToken` is set.

Built-in deployment profiles:

- `small`
  - requests: `250m CPU`, `512Mi`
  - limits: `500m CPU`, `1Gi`
  - recommended for low-traffic chat or light embeddings
- `balanced`
  - requests: `500m CPU`, `1Gi`
  - limits: `1 CPU`, `2Gi`
  - default profile and recommended starting point for most deployments
- `heavy`
  - requests: `1 CPU`, `2Gi`
  - limits: `2 CPU`, `4Gi`
  - recommended for sustained embeddings ingestion or higher concurrency

Select a profile:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set profile=balanced
```

Example values files are also provided:

- [`values-small.yaml`](charts/vertex-openai-proxy/examples/values-small.yaml)
- [`values-balanced-hpa.yaml`](charts/vertex-openai-proxy/examples/values-balanced-hpa.yaml)
- [`values-heavy-ingestion.yaml`](charts/vertex-openai-proxy/examples/values-heavy-ingestion.yaml)
- [`values-production.yaml`](charts/vertex-openai-proxy/examples/values-production.yaml)

By default the selected profile also provides the chart's recommended `EMBEDDING_MAX_CONCURRENCY`:

- `small` -> `4`
- `balanced` -> `8`
- `heavy` -> `12`

You can still override the runtime knob directly:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set profile=balanced \
  --set runtime.embedding.maxConcurrency=10
```

Enable `ServiceMonitor` in Prometheus Operator environments:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set prometheus.serviceMonitor.enabled=true
```

Enable optional HPA:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=6
```

Recommended local verification when `helm` is available:

```bash
helm lint ./charts/vertex-openai-proxy
helm template vertex-openai-proxy ./charts/vertex-openai-proxy
```

For production rollout guidance, see:

- [`docs/runbook.md`](docs/runbook.md)
- [`docs/alerts.md`](docs/alerts.md)

## Grafana Dashboard

An importable overview dashboard is provided at
[`dashboards/vertex-openai-proxy-overview.json`](dashboards/vertex-openai-proxy-overview.json).

It visualizes:

- runtime mode and readiness
- request counts and status class breakdown
- p95 latency and error rates
- effective embedding concurrency and in-flight requests
- queue depth and queue timeouts
- process CPU/RSS and request shedding

## Harness

The repository includes a proxy-native verification harness under [`harness/`](harness).

Primary entrypoints:
- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

See [harness documentation](docs/harness.md) and [release expectations](docs/release.md).
