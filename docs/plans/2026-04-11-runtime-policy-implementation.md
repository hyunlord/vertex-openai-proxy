# Runtime Policy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add correctness-first runtime protections for embeddings and request execution so the proxy remains safe under OpenAI-style array inputs and higher concurrency.

**Architecture:** Keep the current one-input-to-one-upstream-call embedding model, but add bounded concurrency, input-count limits, conservative retry behavior, and stronger observability. Do not introduce provider-specific batching or partial-success semantics.

**Tech Stack:** Python, FastAPI, asyncio, httpx, pytest

---

### Task 1: Add config knobs for runtime policy

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`
- Modify: `README.md`
- Test: `tests/test_settings.py`

**Step 1: Write the failing test**

Add a settings test that loads configuration and asserts these fields exist with expected defaults:
- `embedding_max_concurrency`
- `embedding_max_inputs_per_request`
- `embedding_retry_attempts`
- `embedding_retry_backoff_ms`
- `chat_retry_attempts`
- `chat_retry_backoff_ms`

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_settings.py -q`
Expected: FAIL because the new settings do not exist yet.

**Step 3: Write minimal implementation**

Add the new settings to `app/config.py` with conservative defaults:
- `embedding_max_concurrency=4`
- `embedding_max_inputs_per_request=64`
- `embedding_retry_attempts=1`
- `embedding_retry_backoff_ms=200`
- `chat_retry_attempts=1`
- `chat_retry_backoff_ms=200`

Document them in `.env.example` and `README.md`.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_settings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/config.py .env.example README.md tests/test_settings.py
git commit -m "feat: add runtime policy configuration knobs"
```

### Task 2: Enforce embedding input count limits

**Files:**
- Modify: `app/services/vertex_embeddings.py`
- Test: `tests/test_vertex_embeddings.py`

**Step 1: Write the failing test**

Add a test that builds an embedding request with more than `embedding_max_inputs_per_request` items and expects a `400` response with a clear validation-style message.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: FAIL because oversized requests are not rejected yet.

**Step 3: Write minimal implementation**

Before fan-out starts, check the normalized input count against `settings.embedding_max_inputs_per_request`. If exceeded, raise `HTTPException(status_code=400, detail=...)`.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/vertex_embeddings.py tests/test_vertex_embeddings.py
git commit -m "feat: enforce embedding input count limits"
```

### Task 3: Add bounded concurrency for embedding fan-out

**Files:**
- Modify: `app/services/vertex_embeddings.py`
- Test: `tests/test_vertex_embeddings.py`

**Step 1: Write the failing test**

Add a test that instruments the embedding worker path and proves no more than `embedding_max_concurrency` upstream embedding calls are in flight at once.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: FAIL because current code uses unbounded `asyncio.gather`.

**Step 3: Write minimal implementation**

Introduce an `asyncio.Semaphore(settings.embedding_max_concurrency)` and wrap each `_embed_one` call inside a bounded worker coroutine. Keep output ordering stable.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/vertex_embeddings.py tests/test_vertex_embeddings.py
git commit -m "feat: bound embedding fanout concurrency"
```

### Task 4: Add conservative retry/backoff for embeddings

**Files:**
- Modify: `app/services/vertex_embeddings.py`
- Modify: `app/services/http_client.py`
- Test: `tests/test_vertex_embeddings.py`

**Step 1: Write the failing test**

Add tests that simulate transient embedding failures:
- one `429` followed by success
- one `503` followed by success
- repeated `429/503` that still fail after retry budget

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: FAIL because no retry behavior exists.

**Step 3: Write minimal implementation**

Add a small retry helper around embedding requests:
- retry only on `429` and selected `5xx`
- maximum attempts from config
- async sleep based on `embedding_retry_backoff_ms`
- preserve all-or-nothing behavior

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_vertex_embeddings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/vertex_embeddings.py app/services/http_client.py tests/test_vertex_embeddings.py
git commit -m "feat: add conservative embedding retries"
```

### Task 5: Add chat retry/backoff policy

**Files:**
- Modify: `app/services/vertex_chat.py`
- Modify: `app/services/http_client.py`
- Test: `tests/test_vertex_chat.py`

**Step 1: Write the failing test**

Add tests for chat requests that simulate retry-safe upstream failures:
- one transient `429` then success for non-stream chat
- repeated retry-safe failures that still fail after budget

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_vertex_chat.py -q`
Expected: FAIL because chat has no retry behavior.

**Step 3: Write minimal implementation**

Add conservative retry behavior for non-stream chat requests:
- retry only on `429` and retry-safe `5xx`
- use chat-specific config values
- leave stream retries disabled in v1 to avoid ambiguous partial-stream semantics

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_vertex_chat.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/vertex_chat.py app/services/http_client.py tests/test_vertex_chat.py
git commit -m "feat: add conservative chat retries"
```

### Task 6: Improve observability for runtime policy

**Files:**
- Modify: `app/services/vertex_embeddings.py`
- Modify: `app/services/vertex_chat.py`
- Test: `tests/test_logging.py`

**Step 1: Write the failing test**

Add tests that verify request logs include runtime policy fields such as:
- `input_count`
- `fanout_count`
- `retry_attempts`
- `mode`
- `upstream_status`

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_logging.py -q`
Expected: FAIL because retry metadata is not logged yet.

**Step 3: Write minimal implementation**

Add structured log fields for retry counts and policy-relevant execution details. Keep field names generic and reusable.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_logging.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/vertex_embeddings.py app/services/vertex_chat.py tests/test_logging.py
git commit -m "feat: add runtime policy observability"
```

### Task 7: Document the runtime policy clearly

**Files:**
- Modify: `docs/compatibility.md`
- Modify: `docs/troubleshooting.md`
- Modify: `README.md`
- Test: manual doc review

**Step 1: Update compatibility docs**

Document:
- embeddings are always expanded into one upstream call per input item
- no implicit provider-specific true-batch mode
- embeddings are all-or-nothing
- stream retries are intentionally excluded in v1

**Step 2: Update troubleshooting docs**

Add guidance for:
- input count exceeded
- retry-safe upstream failures
- throughput tuning using concurrency and retry knobs

**Step 3: Update README**

Add a short runtime policy section and list the new environment variables.

**Step 4: Review docs for generic wording**

Check that no customer- or environment-specific wording was introduced.

**Step 5: Commit**

```bash
git add README.md docs/compatibility.md docs/troubleshooting.md
git commit -m "docs: describe runtime policy behavior"
```

### Task 8: Run full verification and close the loop

**Files:**
- No functional file changes required unless verification finds issues

**Step 1: Run all tests**

Run: `python3 -m pytest tests -q`
Expected: PASS

**Step 2: Run harness checks**

Run:
- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

Expected: all PASS

**Step 3: Run local smoke validation**

Run:
- `python3 scripts/smoke_chat.py`
- `python3 scripts/smoke_embeddings.py`

Expected: both return `ok: true`

**Step 4: Commit any final verification-only doc or fixture updates**

```bash
git add .
git commit -m "chore: finalize runtime policy verification"
```

