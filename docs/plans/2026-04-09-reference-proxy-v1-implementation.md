# Reference Proxy V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `vertex-openai-proxy` into a spec-accurate Vertex AI reference proxy for OpenAI-style chat and embeddings, including SSE chat streaming and normalized error handling.

**Architecture:** Keep a single FastAPI service, but split responsibilities cleanly between request validation, internal auth, Vertex auth, protocol adapters, and OpenAI response normalization. Treat chat and embeddings as separate adapters, with embeddings using explicit fan-out and chat supporting both one-shot JSON and SSE relay.

**Tech Stack:** Python, FastAPI, Pydantic, httpx, pytest, pytest-asyncio, Vertex AI REST APIs, GKE Workload Identity

---

### Task 1: Remove Generated Noise And Stabilize Repo Basics

**Files:**
- Modify: `/.gitignore`
- Delete: `app/__pycache__/`
- Delete: `app/routes/__pycache__/`
- Delete: `app/schemas/__pycache__/`
- Delete: `app/services/__pycache__/`

**Step 1: Write the failing cleanliness check**

Add a repo hygiene assertion to CI planning notes: Python bytecode artifacts must not exist in the tracked tree.

**Step 2: Remove tracked cache artifacts**

Delete all tracked `__pycache__` content from the repository.

**Step 3: Verify ignore rules**

Ensure `.gitignore` excludes bytecode and local cache directories.

**Step 4: Run status check**

Run: `git status --short`
Expected: Cache artifacts appear as removed and `.gitignore` reflects the cleanup.

**Step 5: Commit**

```bash
git add .gitignore app
git commit -m "chore: remove generated cache artifacts"
```

### Task 2: Introduce Shared Error Model And Request IDs

**Files:**
- Create: `app/errors.py`
- Create: `app/utils/request_id.py`
- Modify: `app/main.py`
- Test: `tests/test_errors.py`

**Step 1: Write the failing tests**

Create tests asserting:
- every error response contains an OpenAI-style `error` object
- a request id is attached to response headers

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_errors.py -q`
Expected: FAIL because the app does not yet normalize errors or emit request ids.

**Step 3: Add request id middleware**

Generate a request id per request, attach it to `request.state`, and emit `x-request-id` in responses.

**Step 4: Add OpenAI-style error helpers**

Create a reusable error response format:
- `error.message`
- `error.type`
- `error.code`
- optional `error.param`

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_errors.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app tests/test_errors.py
git commit -m "feat: add request ids and normalized error responses"
```

### Task 3: Add Model Allowlist And Capability Registry

**Files:**
- Create: `app/model_registry.py`
- Modify: `app/routes/models.py`
- Modify: `app/routes/chat.py`
- Modify: `app/routes/embeddings.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing tests**

Add tests asserting:
- `/v1/models` returns an explicit allowlist
- unsupported chat models are rejected
- unsupported embedding models are rejected

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: FAIL because there is no registry-backed validation.

**Step 3: Implement model registry**

Represent supported models and simple capabilities:
- chat model ids
- embedding model ids
- whether streaming is supported

**Step 4: Validate incoming model ids**

Reject requests for models not present in the registry with a normalized 4xx response.

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app tests/test_models.py
git commit -m "feat: add model registry and validation"
```

### Task 4: Refine Vertex Auth And HTTP Boundary

**Files:**
- Modify: `app/vertex_auth.py`
- Modify: `app/services/http_client.py`
- Test: `tests/test_vertex_auth.py`

**Step 1: Write the failing tests**

Add tests for:
- metadata token fetch
- token cache reuse
- optional static token override
- upstream HTTP failure mapping

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_vertex_auth.py -q`
Expected: FAIL because auth and HTTP paths are not fully isolated or normalized.

**Step 3: Implement explicit token provider behavior**

Make token acquisition deterministic and easy to mock in tests.

**Step 4: Normalize upstream failures**

Map Vertex and transport errors to project-level error helpers instead of raw FastAPI exceptions.

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_vertex_auth.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app tests/test_vertex_auth.py
git commit -m "feat: harden vertex auth and upstream error mapping"
```

### Task 5: Lock Down Chat Non-Streaming Contract

**Files:**
- Modify: `app/schemas/openai_chat.py`
- Modify: `app/services/vertex_chat.py`
- Modify: `app/routes/chat.py`
- Test: `tests/test_chat_smoke.py`
- Test: `tests/test_chat_contract.py`

**Step 1: Write the failing tests**

Add contract tests asserting:
- response shape matches OpenAI `chat.completion`
- usage is present when available
- request validation rejects malformed `messages`

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_chat_smoke.py tests/test_chat_contract.py -q`
Expected: FAIL because response normalization is currently too thin.

**Step 3: Implement chat response normalization**

Normalize minimal OpenAI-compatible fields:
- `id`
- `object`
- `created`
- `model`
- `choices`
- `usage`

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_chat_smoke.py tests/test_chat_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app tests/test_chat_smoke.py tests/test_chat_contract.py
git commit -m "feat: normalize non-streaming chat responses"
```

### Task 6: Implement Chat SSE Streaming

**Files:**
- Modify: `app/services/http_client.py`
- Modify: `app/services/vertex_chat.py`
- Modify: `app/routes/chat.py`
- Create: `app/schemas/openai_stream.py`
- Test: `tests/test_chat_streaming.py`

**Step 1: Write the failing streaming tests**

Add tests asserting:
- `stream=true` returns `text/event-stream`
- chunk events follow OpenAI `chat.completion.chunk`
- stream ends with `data: [DONE]`

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_chat_streaming.py -q`
Expected: FAIL because streaming currently returns `501`.

**Step 3: Add Vertex streaming client support**

Support upstream streaming requests and line-by-line iteration.

**Step 4: Translate stream chunks to OpenAI SSE**

Emit normalized chunk payloads with stable fields and a final `[DONE]`.

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_chat_streaming.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app tests/test_chat_streaming.py
git commit -m "feat: add chat streaming support"
```

### Task 7: Tighten Embedding Contract And Failure Semantics

**Files:**
- Modify: `app/schemas/openai_embeddings.py`
- Modify: `app/services/vertex_embeddings.py`
- Modify: `app/routes/embeddings.py`
- Test: `tests/test_embeddings.py`
- Test: `tests/test_embeddings_contract.py`

**Step 1: Write the failing tests**

Add tests asserting:
- string input becomes one vector
- list input preserves order
- multi-item failure aborts the entire request
- unsupported non-string items are rejected

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_embeddings.py tests/test_embeddings_contract.py -q`
Expected: FAIL because validation and failure semantics are not fully explicit.

**Step 3: Harden request validation**

Reject unsupported mixed or non-string embedding inputs.

**Step 4: Harden response construction**

Guarantee:
- one vector per item
- ordered indices
- normalized usage fields

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_embeddings.py tests/test_embeddings_contract.py -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app tests/test_embeddings.py tests/test_embeddings_contract.py
git commit -m "feat: harden embeddings contract"
```

### Task 8: Add Structured Logging And Traceability

**Files:**
- Create: `app/utils/logging.py`
- Modify: `app/main.py`
- Modify: `app/services/vertex_chat.py`
- Modify: `app/services/vertex_embeddings.py`
- Test: `tests/test_logging.py`

**Step 1: Write the failing tests**

Add tests asserting:
- request ids appear in log records
- chat and embeddings log model, mode, and upstream latency fields

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_logging.py -q`
Expected: FAIL because logs are not yet structured.

**Step 3: Add structured logging helpers**

Standardize log fields without leaking request payload contents by default.

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_logging.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app tests/test_logging.py
git commit -m "feat: add structured request logging"
```

### Task 9: Publish Compatibility And Operations Docs

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/compatibility.md`
- Create: `docs/troubleshooting.md`
- Create: `docs/roadmap.md`
- Create: `examples/curl/chat.sh`
- Create: `examples/curl/embeddings.sh`
- Create: `examples/python/chat.py`

**Step 1: Write the docs**

Document:
- supported endpoints
- supported request/response fields
- unsupported OpenAI features
- GKE and Workload Identity setup
- common operational failures

**Step 2: Review docs against the code**

Manually verify every documented feature exists in the implementation.

**Step 3: Commit**

```bash
git add README.md docs examples
git commit -m "docs: publish architecture and compatibility guides"
```

### Task 10: Final Verification And Release Prep

**Files:**
- Modify: `Dockerfile`
- Modify: `requirements.txt`
- Create: `.github/workflows/test.yml`

**Step 1: Add or refine test workflow**

Ensure the repository runs tests on push and pull request.

**Step 2: Run the full test suite**

Run: `python3 -m pytest tests -q`
Expected: PASS

**Step 3: Run a local app smoke check**

Run: `python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8080`
Expected: app starts cleanly and `/health` responds with `200`

**Step 4: Prepare release notes**

Summarize:
- supported OpenAI compatibility surface
- current limitations
- next roadmap items

**Step 5: Commit**

```bash
git add .github Dockerfile requirements.txt
git commit -m "chore: finalize reference proxy v1 release prep"
```
