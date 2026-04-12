# Roadmap

## Reference Proxy v1

Completed:

- OpenAI-style `chat.completions`
- OpenAI-style `embeddings`
- SSE chat streaming
- model allowlist and `/v1/models`
- normalized OpenAI-style errors
- structured logging and request correlation
- compatibility and operations docs
- proxy-native harness and release gates

## Operational Reference v1.5

Completed:

- embedding adaptive concurrency
- service-wide runtime modes: `normal`, `elevated`, `degraded`
- `/health`, `/livez`, `/readyz`, `/runtimez`, `/metrics`
- overload protection with request shedding
- bounded queue for short burst smoothing
- Helm chart with optional `ServiceMonitor`
- Grafana dashboard asset
- deployment sizing profiles: `small`, `balanced`, `heavy`
- optional HPA support
- empirical testing log for live and synthetic validation

## Release Candidate

Next priority:

- CI release hardening
- `helm lint` and `helm template` verification in an environment with Helm installed
- stronger Python and curl examples
- release note and versioning flow
- `main` integration and release packaging

## Infrastructure-Blocked Validation

These are not application feature gaps. Treat them as environment validation blockers:

- GKE Workload Identity / STS / VPC Service Controls validation
- in-cluster runtime and metrics validation after policy blockers are resolved
- VM direct validation with the correct Vertex IAM permissions
- final end-to-end rollout check for `/livez`, `/readyz`, `/runtimez`, `/metrics`, chat, and embeddings

## Empirical Track

Continue collecting evidence in [empirical-testing.md](empirical-testing.md):

- bounded queue tuning under mixed chat and embeddings load
- runtime recovery validation: `degraded -> elevated -> normal`
- profile-specific operating guidance for `small`, `balanced`, and `heavy`
- live latency and throughput comparisons across model options

## Production Gateway v2

Future expansion:

- richer logging around complex failure paths
- rate limiting
- richer model routing policy
- broader OpenAI compatibility surface
- optional caching
- policy controls and admin-facing configuration
