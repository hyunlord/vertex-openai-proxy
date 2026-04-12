# Bounded Queue Design

Status: implemented

This document describes a small, bounded queueing strategy for `vertex-openai-proxy`.
It is intentionally conservative and is meant to smooth short request bursts without
turning the proxy into a long-lived job system.

## Why A Bounded Queue

The proxy currently prefers two behaviors:

- accept work immediately when capacity is available
- reject early when overload protection decides the service is under pressure

That is the right default for correctness and for making overload visible, but it can
be unfriendly to short traffic spikes. A very small queue can absorb brief bursts that
would otherwise become avoidable `429` responses.

The queue must remain small for two reasons:

- this is an OpenAI-compatible synchronous API, so clients expect fast success or fast failure
- long queues hide overload, amplify tail latency, and create head-of-line blocking

## Non-Goals

This design does not try to:

- create a durable background job system
- hold requests for many seconds
- guarantee eventual processing after overload
- replace autoscaling or resource tuning

## Approaches Considered

### 1. No Queue

Keep the current design: admit immediately or reject immediately.

Pros:

- simplest behavior
- easy to reason about
- overload is visible right away

Cons:

- avoidable `429` responses during short bursts
- no smoothing for small transient spikes

### 2. Small Bounded Queue

Add a very small in-memory queue with strict limits on depth and wait time.

Pros:

- smooths micro-bursts
- keeps request semantics synchronous
- preserves fast overload visibility because the queue is deliberately small

Cons:

- adds a small amount of runtime complexity
- requires queue metrics and explicit timeout behavior

### 3. Full Async Work Queue

Push accepted work into an internal background queue and process it later.

Pros:

- maximizes burst absorption

Cons:

- changes the service into a different product
- poor fit for synchronous OpenAI-style clients
- high risk of hidden overload and poor tail latency

## Recommendation

Use approach 2.

The proxy should support a small in-memory bounded queue only for short burst smoothing.
Anything beyond that should still fail fast with `429` and an optional `Retry-After`.

## Design Principles

- keep queueing optional and disabled by default
- keep queue depth small
- keep wait budgets short
- degrade toward less queueing, not more queueing
- preserve explainability through metrics and runtime endpoints

## Behavioral Model

### Current Behavior

Today the proxy has no explicit request queue. Requests are either:

- accepted immediately
- rejected by overload protection with `429`
- rejected as invalid input with `400`

### Implemented Behavior

When bounded queueing is enabled:

1. request arrives
2. normal admission check runs
3. if the request can start immediately, it starts immediately
4. if immediate start is not possible but queue policy allows waiting, the request enters a short queue
5. if capacity opens before the queue wait budget expires, the request starts
6. otherwise the request is rejected with `429`

This preserves synchronous request semantics while avoiding long waits.

## Endpoint Policy

### Chat

Chat requests should have the shortest queue budget.

Recommended starting policy:

- small profile: queue wait up to `100ms`, queue depth `2-4`
- balanced profile: queue wait up to `200ms`, queue depth `8`
- heavy profile: queue wait up to `300ms`, queue depth `12`

Reasoning:

- chat users feel latency directly
- long waits are usually worse than a quick retry

### Embeddings

Embeddings can tolerate a slightly longer wait, but only within a tight bound.

Recommended starting policy:

- small profile: queue wait up to `500ms`, queue depth `2`
- balanced profile: queue wait up to `1000ms`, queue depth `4`
- heavy profile: queue wait up to `1500ms`, queue depth `6`

Reasoning:

- embeddings are often backend-driven
- short burst smoothing is useful
- large batch ingestion still should not sit in a long queue

## Runtime Mode Interaction

Queue behavior should follow service-wide runtime mode.

### Normal

- queue enabled if configured
- full queue depth and full wait budget allowed

### Elevated

- queue currently stays at its configured depth and wait budget
- operators should prefer autoscaling and adaptive runtime controls over growing the queue
- future tuning may reduce queue budgets automatically in elevated mode

### Degraded

- queue disabled or nearly disabled
- oversized embeddings requests should still be rejected early
- overload should be visible immediately

This matches the existing service philosophy:

- recover by reducing pressure
- avoid pretending the service has more capacity than it does

## Configuration

Suggested public configuration surface:

- `QUEUE_ENABLED`
- `CHAT_QUEUE_MAX_WAIT_MS`
- `CHAT_QUEUE_MAX_DEPTH`
- `EMBEDDINGS_QUEUE_MAX_WAIT_MS`
- `EMBEDDINGS_QUEUE_MAX_DEPTH`
- `QUEUE_RETRY_AFTER_SECONDS`
- `QUEUE_DISABLE_ON_DEGRADED`

These values should remain conservative by default.

## Error Semantics

Queueing should not change error semantics.

- invalid input still returns `400`
- overload still returns `429`
- upstream failures still map through existing retry and error normalization paths

If a queued request times out before it starts, the proxy returns `429` with a message
that makes it clear the request was shed before execution.

## Metrics And Runtime Visibility

Bounded queueing only makes sense if it is visible.

Implemented metrics:

- `vertex_proxy_queue_depth{endpoint}`
- `vertex_proxy_queue_timeouts_total{endpoint}`
- `vertex_proxy_queue_admissions_total{endpoint}`

Implemented `/runtimez` fields:

- queue enabled flag
- queue depth by endpoint
- queue wait budget by endpoint
- recent queue timeout count

## Operational Guidance

Use queueing to smooth micro-bursts, not to replace capacity planning.

Recommended tuning order:

1. adjust endpoint concurrency
2. adjust replicas and HPA
3. adjust pod resource profile
4. only then consider slightly increasing queue depth

If `429` grows because the queue is constantly full, that is a capacity signal, not a
reason to keep increasing queue size.

## Testing Plan

Verification checklist:

- requests still complete in order and without partial success changes
- queue timeout returns deterministic `429`
- normal mode allows short burst smoothing
- degraded mode reduces or disables queueing
- queue metrics and runtime state are exposed correctly
- bounded queueing does not regress current overload protection behavior

## Summary

The right queue for this proxy is a small, bounded, optional queue that only absorbs
micro-bursts. Long-lived pending work is a poor fit for a synchronous OpenAI-compatible
service and would make overload harder to detect and harder to operate.
