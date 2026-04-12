# Service-Wide Adaptive Runtime Design

## Goal

Evolve `vertex-openai-proxy` from a narrowly correct Vertex/OpenAI compatibility layer into a
platform-oriented operational reference that can adapt safely to changing runtime conditions.

The design must preserve the existing correctness guarantees while allowing the service to react to:

- changing request mix
- changing request rate
- different CPU and memory envelopes
- different upstream behavior
- changing cluster and network conditions

## Positioning

This feature is not intended to turn the proxy into an opaque self-tuning black box.

Instead, the runtime should behave like a guarded operational system:

- operators define safe ranges
- the runtime adapts only inside those ranges
- every decision is observable through logs and metrics
- the system degrades conservatively under pressure

## Non-Goals

- no distributed consensus across replicas
- no provider-specific per-project heuristics
- no speculative batching for embeddings
- no hidden behavior that cannot be explained by logs or metrics

## Design Summary

Introduce a shared runtime controller that:

- tracks recent request health across chat and embeddings
- derives a current runtime mode
- exposes effective settings to request handlers
- emits metrics and logs that explain why the runtime changed behavior

The initial runtime modes are:

- `normal`
- `elevated`
- `degraded`

## Why Shared Runtime Control

Three approaches were considered.

### 1. Per-endpoint controllers

Each endpoint adapts independently.

Pros:

- simple local reasoning

Cons:

- misses service-wide pressure
- duplicates logic

### 2. Shared runtime controller

A single in-process controller observes chat, embeddings, and process health, then derives service
mode and endpoint-specific effective settings.

Pros:

- coherent behavior across the service
- easier to explain and document
- easier to add service-level protection

Cons:

- requires careful interface design

### 3. External policy engine

Move most control to a separate component.

Pros:

- potentially very powerful

Cons:

- too heavy for the current scope
- reduces self-contained open-source usability

The recommended approach is option 2.

## Runtime Modes

### Normal

Use normal service behavior.

- adaptive embedding concurrency may scale up within configured bounds
- standard retry policy applies
- readiness is healthy

### Elevated

The service is still operating normally, but recent signals show growing pressure.

- embedding scale-up is paused or reduced
- chat retries become more conservative
- runtime status reports elevated pressure
- readiness may remain healthy while exposing mode explicitly

### Degraded

The service is under sustained pressure or repeated retryable failure.

- embedding concurrency is reduced rapidly
- request caps are tightened
- optional request shedding may activate
- readiness may report degraded depending on operator policy

## Signals

### Primary signals

These signals determine mode transitions.

- `chat_p95_latency_ms`
- `embeddings_p95_latency_ms`
- `retryable_error_rate`
- `timeout_rate`
- `auth_failure_rate`
- `current_in_flight_chat`
- `current_in_flight_embeddings`

### Secondary signals

These signals help explain and reinforce decisions.

- `process_cpu_percent`
- `process_rss_mb`
- `adaptive_adjustment_frequency`
- `request_rejection_rate`
- `stream_duration_p95`

## Signal Collection

Signals are computed from:

- recent structured request outcomes
- process snapshots sampled in-process
- request lifecycle counters maintained in memory

The runtime should use bounded in-memory sliding windows with:

- size limits
- age limits

This keeps the design self-contained and generic.

## Transition Rules

### Normal to Elevated

Triggered when one or more recent signals exceed soft thresholds, for example:

- embeddings p95 above soft latency threshold
- chat p95 above soft latency threshold
- retryable failure rate above soft threshold
- timeout rate above soft threshold
- in-flight requests above a soft pressure threshold

### Elevated to Degraded

Triggered when stronger signals appear, for example:

- embeddings p95 above hard latency threshold
- chat p95 above hard latency threshold
- retryable failure rate above hard threshold
- timeout rate above hard threshold
- CPU or RSS above hard process thresholds
- pressure remains high despite reduced concurrency

### Recovery

Recovery must be slower than degradation.

- `degraded -> elevated` only after a sustained stable interval
- `elevated -> normal` only after a longer stable interval

## Mode-Dependent Behavior

### Embeddings

Mode affects:

- effective concurrency ceiling
- whether scale-up is allowed
- retry aggressiveness
- optional shedding of oversized requests

Correctness rules remain unchanged:

- one input item still maps to one upstream call
- responses still preserve item count and order
- failures remain all-or-nothing

### Chat

Mode affects:

- in-flight request cap
- retry budget for non-streaming requests
- optional request shedding for overload

Streaming remains conservative and must not retry once partial output has started.

### Health and Readiness

Health endpoints should report:

- current runtime mode
- whether the service is serving
- whether the service is degraded
- whether backpressure or shedding is active

## Metrics

The runtime should expose Prometheus-friendly metrics such as:

- `vertex_proxy_requests_total{endpoint,model,status}`
- `vertex_proxy_request_latency_ms_bucket{endpoint,model}`
- `vertex_proxy_retryable_errors_total{endpoint,status}`
- `vertex_proxy_timeouts_total{endpoint}`
- `vertex_proxy_in_flight_requests{endpoint}`
- `vertex_proxy_effective_embedding_concurrency`
- `vertex_proxy_runtime_mode`
- `vertex_proxy_adaptive_adjustments_total{reason}`
- `vertex_proxy_process_cpu_percent`
- `vertex_proxy_process_rss_mb`

## Logging

Runtime logs should make every state transition explainable.

Important events:

- mode changed
- adaptive concurrency adjusted
- overload protection triggered
- request shedding activated
- readiness degraded or restored

Each event should include relevant recent metrics in structured form.

## Configuration Philosophy

Adaptive runtime remains guarded by configuration.

Operators should be able to set:

- enable or disable runtime adaptation
- safe min and max ranges
- soft and hard thresholds
- recovery cooldowns
- request cap and shedding behavior

Defaults should remain conservative and easy to reason about.

## Rollout Plan

1. introduce shared runtime controller in-process
2. add metric and state surfaces
3. keep adaptive service-wide mode disabled by default
4. validate with synthetic failure tests
5. validate with empirical live tests
6. document operational guidance

## Recommendation

Build service-wide adaptation as a transparent runtime controller, not as an opaque auto-tuner.
The winning traits for this project are:

- correctness first
- controlled adaptation
- rich observability
- clear operator control
