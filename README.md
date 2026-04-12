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
- `CHAT_RETRY_ATTEMPTS`: Retry budget for retry-safe non-stream chat failures
- `CHAT_RETRY_BACKOFF_MS`: Backoff between chat retries in milliseconds
- `VERTEX_ACCESS_TOKEN`: Optional manual token override for local debugging

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

## Harness

The repository includes a proxy-native verification harness under [`.vertex-proxy`](.vertex-proxy) and [`harness/`](harness).

Primary entrypoints:
- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

See [harness documentation](docs/harness.md) and [release expectations](docs/release.md).
