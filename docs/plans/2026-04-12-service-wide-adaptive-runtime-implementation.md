# Service-Wide Adaptive Runtime Implementation Plan

## Objective

Implement a shared runtime controller that can observe request health across the proxy and derive
service-wide runtime modes without changing the current correctness guarantees.

## Milestones

1. shared runtime state
2. runtime metrics and mode surfaces
3. embeddings integration
4. chat integration
5. readiness integration
6. overload protection
7. docs and empirical validation

## Task Breakdown

### Task 1: Add runtime controller module

Files:

- `app/runtime/controller.py`
- `app/runtime/types.py`
- `tests/test_runtime_controller.py`

Changes:

- define runtime modes
- track recent request outcomes across endpoints
- track in-flight counts
- expose current mode
- support soft and hard thresholds

Verification:

- mode transition unit tests
- cooldown and recovery tests

### Task 2: Add runtime metrics interface

Files:

- `app/runtime/metrics.py`
- `tests/test_runtime_metrics.py`

Changes:

- compute p95 latency per endpoint
- compute retryable error rates
- compute timeout rates
- track CPU and RSS snapshots

Verification:

- metric aggregation tests

### Task 3: Integrate embeddings with shared runtime

Files:

- `app/services/vertex_embeddings.py`
- `tests/test_embeddings.py`

Changes:

- embeddings consume service mode and effective settings from the shared runtime controller
- adaptive concurrency remains bounded by operator configuration
- degraded mode may reduce ceiling or disable scale-up

Verification:

- embeddings correctness unchanged
- embeddings adapt to runtime mode

### Task 4: Integrate chat with shared runtime

Files:

- `app/services/vertex_chat.py`
- `tests/test_chat_contract.py`
- `tests/test_runtime_chat_policy.py`

Changes:

- add chat in-flight tracking
- add runtime-aware retry budget
- prepare optional request cap behavior

Verification:

- chat correctness unchanged
- runtime mode influences retry/cap behavior

### Task 5: Add health and readiness surfaces

Files:

- `app/routes/health.py`
- `tests/test_health.py`

Changes:

- include runtime mode
- include degraded indicators
- include readiness-safe operator visibility

Verification:

- health payload tests

### Task 6: Add metrics endpoint

Files:

- `app/routes/metrics.py`
- `tests/test_metrics.py`
- `README.md`

Changes:

- expose Prometheus-friendly metrics
- document metric names and recommended dashboards

Verification:

- metrics output tests

### Task 7: Add overload protection primitives

Files:

- `app/runtime/controller.py`
- `app/services/vertex_chat.py`
- `app/services/vertex_embeddings.py`
- `tests/test_runtime_overload.py`

Changes:

- optional request caps
- optional low-priority shedding hooks

Verification:

- overload tests under synthetic pressure

### Task 8: Update docs and empirical log

Files:

- `README.md`
- `docs/architecture.md`
- `docs/operations-transition.md`
- `docs/troubleshooting.md`
- `docs/empirical-testing.md`

Changes:

- document runtime modes
- document adaptive observability
- record live and synthetic findings

## Guardrails

- keep service-wide adaptation disabled by default until validated
- keep embedding correctness semantics unchanged
- do not add provider-specific or project-specific logic
- ensure every adaptive action is visible in logs and metrics
- preserve fixed, deterministic fallback behavior

## Verification Commands

- `python3 -m pytest tests -q`
- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

## Exit Criteria

- runtime modes are observable and test-covered
- embeddings and chat both consume shared runtime signals safely
- health and metrics make the adaptive state easy to understand
- operator guidance is documented clearly
