# Runbook

## Purpose

Use this runbook to roll out, verify, scale, and roll back `vertex-openai-proxy` in Kubernetes.

## Recommended Starting Point

- use the Helm chart
- start with the `balanced` profile
- start with `replicaCount: 2`
- enable HPA and `ServiceMonitor`
- provide `INTERNAL_BEARER_TOKEN` through an existing Kubernetes secret

Starter values:

- [`charts/vertex-openai-proxy/examples/values-production.yaml`](../charts/vertex-openai-proxy/examples/values-production.yaml)

## Pre-Deployment Checks

Before rollout:

- the release image tag exists and is pullable
- the auth secret exists
- the target Vertex project, location, and models are set
- `helm lint ./charts/vertex-openai-proxy` passes
- `helm template vertex-openai-proxy ./charts/vertex-openai-proxy` passes
- `python3 -m pytest tests -q` passes in CI
- `bash scripts/verify_full.sh` passes in CI

## Rollout

Install or upgrade with Helm:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  -f charts/vertex-openai-proxy/examples/values-production.yaml \
  --set image.repository=your-registry/vertex-openai-proxy \
  --set image.tag=your-release-tag \
  --set config.vertexProjectId=your-gcp-project-id
```

Wait for rollout:

```bash
kubectl rollout status deployment/vertex-openai-proxy
```

## Post-Rollout Verification

Verify the pod is live and ready:

```bash
kubectl port-forward deployment/vertex-openai-proxy 8080:8080
curl -s http://127.0.0.1:8080/livez
curl -s http://127.0.0.1:8080/readyz
curl -s http://127.0.0.1:8080/runtimez
curl -s http://127.0.0.1:8080/metrics
```

Minimum success checks:

- `/livez` returns `200`
- `/readyz` returns `200`
- `/runtimez` shows `mode: normal` or an explainable transitional mode
- `/metrics` exposes `vertex_proxy_runtime_mode`

Then verify request flow:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`

If `mock/local` and `vm direct` pass but in-cluster calls fail with policy or perimeter errors, treat that as an infrastructure blocker first.

## Scaling Guidance

Use these signals before changing pod size:

- if `vertex_proxy_request_shed_total` increases, add replicas first
- if `vertex_proxy_request_p95_latency_ms{scope="embeddings"}` stays high, review embedding concurrency and replica count
- if `vertex_proxy_process_rss_mb` stays high, move from `balanced` to `heavy`
- if the service stays in `degraded`, reduce pressure and scale out before raising limits

Order of operations:

1. adjust runtime knobs
2. increase replicas or HPA range
3. increase pod profile

## Rollback

Show Helm history:

```bash
helm history vertex-openai-proxy
```

Rollback to the previous revision:

```bash
helm rollback vertex-openai-proxy <revision>
kubectl rollout status deployment/vertex-openai-proxy
```

After rollback, repeat:

- `/livez`
- `/readyz`
- `/runtimez`
- `/metrics`

## Incident Triage

Use this quick split:

- only `in-cluster` fails:
  - check Workload Identity, STS, IAM, and perimeter policy
- `vm direct` also fails:
  - check image, config, auth secret, and release version
- `readyz` fails but `livez` passes:
  - inspect `/runtimez` for `mode`, `reasons`, queue depth, and in-flight pressure
- `request_shed_total` rises:
  - scale out or reduce pressure

## Safe Defaults

- keep bounded queueing short
- keep `readinessFailOnDegraded` conservative unless you have enough replicas
- prefer `balanced` before `heavy`
- document every production override in Helm values, not ad-hoc shell history
