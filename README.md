# vertex-openai-proxy

Reference OpenAI-compatible proxy for Vertex AI.

This service accepts a focused OpenAI-compatible API surface and forwards requests to Vertex AI using Workload Identity, ADC, or metadata-based access tokens. It is designed as a narrow, predictable compatibility layer rather than a multi-provider gateway.

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
- no tool-calling compatibility layer yet
- embeddings intentionally fail the entire request if any item fails

See [architecture](docs/architecture.md), [compatibility](docs/compatibility.md), [troubleshooting](docs/troubleshooting.md), and [roadmap](docs/roadmap.md) for details.

For real-world tuning and model behavior history, see the running [empirical testing log](docs/empirical-testing.md). Future live model tests should be appended there instead of being kept only in ad-hoc notes.

## Runtime Policy

This proxy prefers correctness over speculative batching.

- embeddings always normalize list input into one upstream call per input item
- embeddings preserve input order and return one vector per item
- embeddings use bounded fan-out concurrency instead of implicit true batch behavior
- embeddings fail the whole request if any item fails
- non-stream chat uses conservative retries for retry-safe upstream failures
- stream chat avoids retries after a stream starts to prevent ambiguous partial output

The runtime knobs are conservative by default so the proxy remains predictable under array inputs and moderate concurrency.

## Environment Variables

Start by copying the example file:

```bash
cp .env.example .env
```

- `INTERNAL_BEARER_TOKEN`: Shared secret used by the client when calling this proxy
- `VERTEX_PROJECT_ID`: Google Cloud project ID
- `VERTEX_CHAT_LOCATION`: Chat endpoint location such as `global`
- `VERTEX_EMBEDDING_LOCATION`: Embedding endpoint location such as `us-central1`
- `VERTEX_CHAT_MODEL`: Default chat model ID
- `VERTEX_EMBEDDING_MODEL`: Default embedding model ID
- `REQUEST_TIMEOUT_SECONDS`: Upstream timeout
- `EMBEDDING_MAX_CONCURRENCY`: Maximum in-flight upstream embedding calls per request
- `EMBEDDING_MAX_INPUTS_PER_REQUEST`: Hard cap for input items in one embeddings request
- `EMBEDDING_RETRY_ATTEMPTS`: Retry budget for retry-safe embedding failures
- `EMBEDDING_RETRY_BACKOFF_MS`: Backoff between embedding retries in milliseconds
- `EMBEDDING_ADAPTIVE_CONCURRENCY`: Enable optional step-based adaptive fan-out for embeddings
- `EMBEDDING_ADAPTIVE_MAX_CONCURRENCY`: Upper bound for adaptive embedding concurrency
- `EMBEDDING_ADAPTIVE_WINDOW_SIZE`: Number of recent embedding requests to consider
- `EMBEDDING_ADAPTIVE_WINDOW_SECONDS`: Maximum age of adaptive request history
- `EMBEDDING_ADAPTIVE_COOLDOWN_SECONDS`: Minimum time between adaptive adjustments
- `EMBEDDING_ADAPTIVE_MIN_SAMPLES`: Minimum recent requests required before adaptive changes
- `EMBEDDING_ADAPTIVE_LATENCY_UP_THRESHOLD_MS`: Healthy p95 latency threshold for scale-up
- `EMBEDDING_ADAPTIVE_LATENCY_DOWN_THRESHOLD_MS`: Unhealthy p95 latency threshold for scale-down
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_UP_THRESHOLD`: Maximum retryable failure rate for scale-up
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_DOWN_THRESHOLD`: Retryable failure rate that triggers scale-down
- `RUNTIME_ADAPTIVE_MODE`: Enable service-wide runtime mode awareness across chat and embeddings
- `READINESS_FAIL_ON_DEGRADED`: Return `503` from `/readyz` while in degraded mode
- `RUNTIME_WINDOW_SIZE`: Number of recent requests kept in the shared runtime window
- `RUNTIME_WINDOW_SECONDS`: Maximum age of the shared runtime window
- `RUNTIME_RECOVERY_SECONDS`: Required stable interval before recovering from elevated or degraded mode
- `RUNTIME_SOFT_IN_FLIGHT_CHAT`: Soft in-flight chat threshold for elevated mode
- `RUNTIME_HARD_IN_FLIGHT_CHAT`: Hard in-flight chat threshold for degraded mode
- `RUNTIME_SOFT_IN_FLIGHT_EMBEDDINGS`: Soft in-flight embeddings threshold for elevated mode
- `RUNTIME_HARD_IN_FLIGHT_EMBEDDINGS`: Hard in-flight embeddings threshold for degraded mode
- `CHAT_MAX_IN_FLIGHT_REQUESTS`: Absolute chat admission cap regardless of runtime mode
- `EMBEDDINGS_MAX_IN_FLIGHT_REQUESTS`: Absolute embeddings admission cap regardless of runtime mode
- `RUNTIME_DEGRADED_CHAT_MAX_IN_FLIGHT`: Tighter degraded-mode chat admission cap
- `RUNTIME_DEGRADED_EMBEDDINGS_MAX_IN_FLIGHT`: Tighter degraded-mode embeddings admission cap
- `RUNTIME_DEGRADED_MAX_EMBEDDING_INPUTS`: Maximum embeddings input items accepted while degraded
- `RUNTIME_CHAT_SOFT_LATENCY_MS`: Soft p95 chat latency threshold for entering elevated mode
- `RUNTIME_CHAT_HARD_LATENCY_MS`: Hard p95 chat latency threshold for entering degraded mode
- `RUNTIME_EMBEDDINGS_SOFT_LATENCY_MS`: Soft p95 embeddings latency threshold for entering elevated mode
- `RUNTIME_EMBEDDINGS_HARD_LATENCY_MS`: Hard p95 embeddings latency threshold for entering degraded mode
- `RUNTIME_SOFT_RETRYABLE_ERROR_RATE`: Soft retryable failure rate threshold for elevated mode
- `RUNTIME_HARD_RETRYABLE_ERROR_RATE`: Hard retryable failure rate threshold for degraded mode
- `RUNTIME_SOFT_TIMEOUT_RATE`: Soft timeout rate threshold for elevated mode
- `RUNTIME_HARD_TIMEOUT_RATE`: Hard timeout rate threshold for degraded mode
- `RUNTIME_HARD_CPU_PERCENT`: Hard CPU pressure threshold for degraded mode
- `RUNTIME_HARD_RSS_MB`: Hard memory pressure threshold for degraded mode
- `QUEUE_ENABLED`: Enable optional bounded queueing for short burst smoothing
- `QUEUE_DISABLE_ON_DEGRADED`: Disable bounded queueing while the service is degraded
- `QUEUE_POLL_INTERVAL_MS`: Poll interval used while a request waits for bounded queue admission
- `QUEUE_RETRY_AFTER_SECONDS`: Suggested retry window for shed requests
- `CHAT_QUEUE_MAX_WAIT_MS`: Maximum wait budget for queued chat requests
- `CHAT_QUEUE_MAX_DEPTH`: Maximum queued chat requests
- `EMBEDDINGS_QUEUE_MAX_WAIT_MS`: Maximum wait budget for queued embeddings requests
- `EMBEDDINGS_QUEUE_MAX_DEPTH`: Maximum queued embeddings requests
- `CHAT_RETRY_ATTEMPTS`: Retry budget for retry-safe non-stream chat failures
- `CHAT_RETRY_BACKOFF_MS`: Backoff between chat retries in milliseconds
- `VERTEX_ACCESS_TOKEN`: Optional manual token override for local debugging

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

## Quick Start

1. Install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Export configuration:
```bash
cp .env.example .env
export INTERNAL_BEARER_TOKEN=change-me
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

## VM Direct Validation

When GKE pod-to-Vertex auth is blocked but the ops VM can still call Vertex, use Docker on the VM as a verification-only path:

```bash
docker build -t vertex-openai-proxy:local .
docker run --rm -p 8080:8080 \
  -e INTERNAL_BEARER_TOKEN=change-me \
  -e VERTEX_PROJECT_ID=your-gcp-project-id \
  -e VERTEX_CHAT_LOCATION=global \
  -e VERTEX_EMBEDDING_LOCATION=us-central1 \
  vertex-openai-proxy:local
```

Then run:

```bash
export PROXY_BASE_URL=http://127.0.0.1:8080
export INTERNAL_BEARER_TOKEN=change-me
python3 scripts/smoke_vm_direct.py
```

This path is for verification only. Keep production traffic on GKE after perimeter and STS policy issues are resolved.

## In-Cluster Validation

Use this path only when GKE Workload Identity and perimeter policy are expected to be healthy:

```bash
export IN_CLUSTER_PROXY_BASE_URL=http://your-service-name:8080
export INTERNAL_BEARER_TOKEN=change-me
python3 scripts/smoke_in_cluster.py
```

If `mock/local` passes and `vm direct` passes but `in-cluster` fails with `organization's policy` or `vpcServiceControlsUniqueIdentifier`, treat it as an infrastructure blocker first.

## GKE / Workload Identity

This service is meant to run on GKE with a Kubernetes service account mapped to a Google service account that can call Vertex AI. At minimum, the mapped GSA needs Vertex prediction permissions for the target models.

## Examples

- [curl chat example](examples/curl/chat.sh)
- [curl embeddings example](examples/curl/embeddings.sh)
- [Python chat example](examples/python/chat.py)

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
