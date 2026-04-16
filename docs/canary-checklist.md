# Canary Checklist

## Purpose

Use this checklist when promoting a new `vertex-openai-proxy` release into a private cluster with a small canary footprint before stable rollout.

## Pre-Canary Checks

- the release tag and image digest are known
- the private repo points at the intended chart version and image tag
- `INTERNAL_BEARER_TOKEN` secret exists in the target namespace
- Workload Identity binding is present
- Vertex IAM permissions are present for the target models
- perimeter, STS, and VPC policy are expected to allow Vertex access

## Recommended Canary Shape

- profile: `balanced`
- replicas: `1`
- HPA: off or minimum `1`
- bounded queue: enabled
- adaptive runtime: enabled
- ServiceMonitor: enabled

## Rollout

1. update the canary image tag only
2. deploy the canary release
3. wait for rollout completion
4. verify health and metrics before sending real traffic

## Immediate Verification

- `GET /livez`
- `GET /readyz`
- `GET /runtimez`
- `GET /metrics`
- `GET /v1/models`

Success means:

- `/livez` returns `200`
- `/readyz` returns `200`
- `/runtimez` is in `normal` or an explainable short-lived `elevated` state
- `/metrics` exposes `vertex_proxy_runtime_mode`

## Functional Smoke Checks

- one chat request succeeds
- one non-stream tool-calling request succeeds
- one streaming tool-calling request succeeds
- one embeddings request succeeds
- one real application path succeeds

## Canary Observation Window

Observe for at least `15-30 minutes` before promotion.

Track:

- `vertex_proxy_runtime_mode`
- `vertex_proxy_runtime_ready`
- `vertex_proxy_request_p95_latency_ms`
- `vertex_proxy_request_shed_total`
- `vertex_proxy_queue_timeouts_total`
- `vertex_proxy_retryable_error_rate`
- `vertex_proxy_timeout_rate`
- `vertex_proxy_process_rss_mb`
- `vertex_proxy_process_cpu_percent`

## Promote To Stable When

- runtime stays `normal`
- no unexpected `degraded` transitions
- `vertex_proxy_request_shed_total` does not increase
- chat and embeddings succeed consistently
- latency stays inside expected canary range

## Rollback Immediately When

- `/readyz` fails
- runtime stays `degraded`
- `vertex_proxy_request_shed_total` increases repeatedly
- `vertex_proxy_queue_timeouts_total` increases repeatedly
- Vertex calls fail with IAM, STS, or perimeter errors
- application traffic shows repeated failures

## Rollback Notes

- roll back the canary release first
- keep stable untouched unless the stable lane also regressed
- after rollback, re-check `/livez`, `/readyz`, `/runtimez`, and `/metrics`

## Evidence To Capture

- canary image tag and digest
- request IDs for failed requests
- `runtimez` snapshot
- `vertex_proxy_runtime_mode` state
- any `organization's policy` or `vpcServiceControlsUniqueIdentifier` response details
