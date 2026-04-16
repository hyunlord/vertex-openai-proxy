# Roadmap

## Guiding Order

Use this priority order for every change:

1. keep the repository usable as real open source
2. keep the GKE / GenOS serving path stable
3. improve reliability and compatibility without losing the narrow Vertex-first scope

This project is not trying to become a generic multi-provider gateway. The
target position is:

- a Vertex AI on GKE reference proxy
- a focused OpenAI-compatible compatibility layer
- an operational reference with strong observability and predictable failure behavior

## What Is Already Complete

### Reference Proxy v1

- OpenAI-style `chat.completions`
- OpenAI-style `embeddings`
- SSE chat streaming
- model allowlist and `/v1/models`
- normalized OpenAI-style errors
- structured logging and request correlation
- compatibility and operations docs
- proxy-native harness and release gates

### Operational Reference v1.5

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

## Phase 0: Open-Source Baseline

Goal:

- make the repository clearly usable as public open source without changing live runtime behavior

Priority items:

- add `LICENSE`
- add `CONTRIBUTING.md`
- separate development dependencies from runtime dependencies
- make the README explicitly position the project as a Vertex/GKE reference proxy

Acceptance criteria:

- the repo root contains `LICENSE`
- the repo root contains `CONTRIBUTING.md`
- test-only dependencies are not installed by the production Docker image
- CI still runs `pytest`, `verify_*`, and Helm validation successfully

## Phase 1: Runtime Hardening

Goal:

- fix the highest-confidence runtime issues without widening API scope

Priority items:

- shared `httpx.AsyncClient` instead of per-request client construction
- move ADC token refresh off the main event loop
- guard token cache updates
- replace the current embeddings fan-out error path with a cancellation-safe structure

Acceptance criteria:

- request handling no longer constructs a new HTTP client for every upstream call
- token refresh no longer performs synchronous network work on the event loop
- embeddings failure does not leave best-effort background calls running after the request is already failed
- existing chat, embeddings, and verification scripts remain green

## Phase 2: OpenAI Core Compatibility

Goal:

- cover the most commonly expected `chat.completions` compatibility features while staying Vertex-first

Priority items:

- tool calling request fields: `tools`, `tool_choice`
- assistant tool call responses: `tool_calls`
- `tool` role messages
- richer chat content schema that can grow beyond plain text

Acceptance criteria:

- non-streaming and streaming tool-calling round-trips are covered by contract tests
- request and response schemas no longer force `content: str` for all chat messages
- the README no longer lists tool calling as a missing core capability

## Phase 3: Streaming And Usage Semantics

Goal:

- make compatibility more precise where today it is conservative or approximate

Priority items:

- mid-stream error policy and SSE behavior
- clarify or improve embeddings `usage` accounting
- tighten chunk normalization semantics for OpenAI client expectations

Acceptance criteria:

- streaming contract behavior is documented and tested
- embeddings `usage` is either more accurate or explicitly marked as approximate in behavior and docs

## Phase 4: Operator Experience Simplification

Goal:

- keep the operational depth, but reduce the barrier for first-time users

Priority items:

- split docs into quickstart guidance versus operator guidance
- present a small required env surface and move advanced knobs into a separate section
- keep Helm examples layered as simple / production / advanced

Acceptance criteria:

- first-time setup requires only a small core set of environment variables
- advanced runtime knobs stay available but are documented separately
- operator docs remain detailed without overwhelming first-time readers

## Phase 5: Production Gateway v2

Future expansion after the above is stable:

- richer logging around complex failure paths
- rate limiting
- richer model routing policy
- optional caching
- policy controls and admin-facing configuration
- carefully chosen compatibility surface expansion beyond today's scope

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
