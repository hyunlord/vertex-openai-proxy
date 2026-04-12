# Adaptive Concurrency Implementation Plan

## Objective

Implement an optional, pod-local adaptive concurrency controller for embeddings without changing
existing correctness guarantees or the default fixed-concurrency behavior.

## Milestones

1. configuration surface
2. adaptive state model
3. controller logic
4. embeddings integration
5. observability
6. tests
7. empirical validation

## Task Breakdown

### Task 1: Add configuration flags

Files:

- `app/config.py`
- `.env.example`
- `README.md`

Changes:

- add adaptive mode toggle
- add adaptive max concurrency
- add window size and time settings
- add latency and failure thresholds
- add cooldown setting

Verification:

- config unit tests for defaults and overrides

### Task 2: Add adaptive controller module

Files:

- `app/services/adaptive_concurrency.py`
- `tests/test_adaptive_concurrency.py`

Changes:

- define request outcome record
- define sliding window storage
- compute aggregate metrics
- implement ladder transitions
- enforce cooldown

Verification:

- unit tests for scale up and scale down
- cooldown tests
- threshold boundary tests

### Task 3: Integrate with embedding execution path

Files:

- `app/services/vertex_embeddings.py`
- `tests/test_embeddings.py`

Changes:

- compute `effective_concurrency`
- use adaptive controller only when enabled
- record request outcomes after completion
- preserve fixed behavior when disabled

Verification:

- fixed mode behavior unchanged
- adaptive mode uses step ladder
- response contract remains unchanged

### Task 4: Add structured adjustment logs

Files:

- `app/utils/logging.py`
- `app/services/vertex_embeddings.py`
- `tests/test_logging.py`

Changes:

- log request-level configured vs effective concurrency
- log controller adjustments with reason and metrics

Verification:

- log payload tests

### Task 5: Add failure-path integration tests

Files:

- `tests/test_adaptive_concurrency.py`
- `tests/test_embeddings.py`

Changes:

- simulate retryable upstream failures
- simulate timeout-heavy window
- assert downscale behavior

Verification:

- all new tests pass

### Task 6: Update docs

Files:

- `README.md`
- `docs/architecture.md`
- `docs/compatibility.md`
- `docs/troubleshooting.md`
- `docs/empirical-testing.md`

Changes:

- document adaptive mode as optional
- explain defaults and recommendations
- add troubleshooting guidance for mis-tuned concurrency
- record empirical results after implementation

Verification:

- doc review for generic language and no environment-specific details

## Guardrails

- do not change chat behavior
- do not add distributed shared state
- do not alter the one-input-one-upstream-call embedding policy
- do not enable adaptive mode by default
- keep the feature generic and provider-agnostic in terminology

## Verification Commands

- `python3 -m pytest tests -q`
- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

## Exit Criteria

- adaptive mode is fully optional and disabled by default
- fixed mode behavior is unchanged
- embeddings correctness contract remains intact
- logs explain controller behavior clearly
- empirical testing shows stable scale-up and fast scale-down behavior
