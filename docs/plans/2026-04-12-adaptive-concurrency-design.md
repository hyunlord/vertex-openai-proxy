# Adaptive Concurrency Design

## Goal

Add an optional, conservative adaptive concurrency mode for embeddings that preserves the existing
correctness contract:

- one input item maps to one upstream Vertex embedding call
- input count always matches response vector count
- failures remain all-or-nothing

The feature should improve throughput under healthy conditions while backing off quickly when
upstream or environment pressure increases.

## Non-Goals

- No adaptive batching for embeddings
- No synthetic batching for chat completions
- No shared distributed coordination across pods
- No provider-specific branching beyond generic upstream health signals

## Constraints

- The proxy must remain generic and safe for public open-source use
- The existing fixed concurrency mode must remain available and be the default
- Adaptive behavior must be easy to reason about, log, and disable
- Any reduction in latency must never come at the cost of response misalignment

## Recommended Approach

Use a pod-local, step-based adaptive concurrency controller.

The controller derives an `effective_concurrency` from:

- a configured base concurrency
- a configured maximum adaptive ceiling
- recent embedding request outcomes

The controller only moves across a small fixed ladder, for example:

- 4
- 8
- 12
- 16

This avoids opaque or overly reactive tuning and makes behavior easy to explain in logs and docs.

## Why Step-Based Instead Of Fully Dynamic

Three candidate approaches were considered.

### 1. Fixed concurrency only

This is the current behavior.

Pros:

- simple
- predictable
- easy to debug

Cons:

- cannot react to changing cluster or upstream conditions
- leaves throughput on the table in healthy environments

### 2. Step-based adaptive concurrency

This proposal.

Pros:

- more resilient than fixed tuning
- easier to test than continuous control loops
- easier to explain to operators
- safe to disable

Cons:

- slightly more implementation complexity
- still pod-local rather than globally coordinated

### 3. Fully dynamic concurrency control

Examples include highly reactive control loops or AIMD-style continuous tuning.

Pros:

- potentially best performance

Cons:

- harder to validate
- harder to debug
- higher risk of oscillation and poor open-source defaults

The recommended approach is option 2.

## Runtime Model

Adaptive mode applies only to `/v1/embeddings`.

For each embedding request:

1. normalize inputs
2. determine current `effective_concurrency`
3. process items with bounded concurrency using a semaphore sized to that value
4. record request outcome metrics
5. update adaptive state if cooldown and decision rules allow

## Signals

The controller should only rely on generic upstream health signals already observable by the proxy.

Suggested signals:

- recent request error rate
- recent retryable upstream failures
- recent timeout count
- recent p95 latency
- recent average latency

These should be computed over a pod-local sliding window.

## Windowing

Use a bounded in-memory sliding window with two limits:

- a max number of recent requests
- a max age in seconds

Recommended initial values:

- last 20 embedding requests
- last 60 seconds

These limits are simple, cheap, and easy to explain.

## Adjustment Rules

### Downscale quickly

Reduce one step when any of the following occurs:

- retryable failure rate exceeds threshold
- timeout count exceeds threshold
- p95 latency exceeds threshold

Suggested first thresholds:

- retryable failure rate > 10%
- timeout rate > 5%
- p95 latency > 8000 ms

### Upscale slowly

Increase one step only when all of the following are true:

- failure rate is effectively zero or near zero
- timeout rate is zero
- p95 latency is below target
- the controller has remained stable for a full cooldown interval

Suggested first thresholds:

- failure rate < 1%
- timeout rate = 0
- p95 latency < 4000 ms

## Cooldown

To avoid oscillation, changes should be rate-limited.

Recommended behavior:

- at most one step change per 30 seconds

When instability is detected, downscale immediately if cooldown has elapsed.
When health is improving, upscale only after a full stable interval.

## Configuration

Add optional settings such as:

- `EMBEDDING_ADAPTIVE_CONCURRENCY=false`
- `EMBEDDING_ADAPTIVE_MAX_CONCURRENCY=16`
- `EMBEDDING_ADAPTIVE_WINDOW_SIZE=20`
- `EMBEDDING_ADAPTIVE_WINDOW_SECONDS=60`
- `EMBEDDING_ADAPTIVE_COOLDOWN_SECONDS=30`
- `EMBEDDING_ADAPTIVE_LATENCY_UP_THRESHOLD_MS=4000`
- `EMBEDDING_ADAPTIVE_LATENCY_DOWN_THRESHOLD_MS=8000`
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_UP_THRESHOLD=0.01`
- `EMBEDDING_ADAPTIVE_FAILURE_RATE_DOWN_THRESHOLD=0.10`

The existing `EMBEDDING_MAX_CONCURRENCY` remains the starting point and fixed-mode fallback.

## State Management

Keep controller state in process memory only.

State includes:

- current effective concurrency
- last adjustment timestamp
- recent request records

This keeps the feature generic and avoids introducing Redis or shared state.

## Logging And Observability

Every embedding request should log:

- configured concurrency
- effective concurrency
- adaptive mode enabled or disabled
- input count
- retry attempts
- upstream status
- latency

Every controller adjustment should log a structured event with:

- previous concurrency
- new concurrency
- reason for change
- current observed metrics

## Failure Semantics

Adaptive mode must not change correctness semantics.

The following remain true:

- partial success is not allowed
- malformed upstream payloads still fail the request
- retries remain conservative
- auth and policy errors remain explicit

Adaptive mode only changes internal scheduling of already independent embedding calls.

## Safe Defaults

Recommended public defaults:

- adaptive mode disabled by default
- fixed concurrency default remains 4

Recommended operator guidance:

- start fixed mode at 4 or 8
- enable adaptive mode only after basic observability is in place
- cap adaptive mode at 16 initially

## Test Strategy

### Unit tests

- window aggregation
- threshold decisions
- cooldown behavior
- step ladder transitions

### Integration tests

- healthy upstream should scale up gradually
- repeated retryable failures should scale down
- timeouts should scale down
- adaptive mode off should preserve fixed behavior

### Empirical validation

Document measured results in `docs/empirical-testing.md` using:

- fixed concurrency baselines
- adaptive mode under stable load
- adaptive mode under injected retryable failures
- adaptive mode under concurrent requests

## Rollout Plan

1. implement controller in pod-local memory
2. add structured logs and tests
3. keep feature disabled by default
4. document operator guidance
5. validate with empirical tests before considering a default change

## Recommendation

Implement adaptive concurrency as an optional, step-based controller for embeddings only.
Keep fixed concurrency as the default and primary documented mode. Use adaptive mode as an
advanced operator feature once enough empirical evidence is collected.
