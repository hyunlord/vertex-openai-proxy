# Runtime Policy Design

## Goal

Define a safe and portable runtime policy for `vertex-openai-proxy` that favors correctness first and only then improves throughput. The policy must remain generic and must not assume behavior that is only true for one deployment or one customer environment.

## Design Principles

1. Correctness before throughput
2. Explicit contracts over implicit provider behavior
3. Conservative defaults, configurable tuning
4. Generic behavior across providers and environments
5. No silent partial success for embeddings

## Key Observations

- OpenAI-compatible clients often send embedding inputs as arrays.
- `gemini-embedding-2-preview` returns a single embedding for a single `content` payload, even when that payload contains multiple `parts`.
- Therefore, a `parts[]` request must not be treated as equivalent to `input[] -> data[]`.
- Chat requests map cleanly to a single upstream request.
- Embedding correctness depends on preserving `N inputs -> N vectors`.

## Recommended Runtime Policy

### Embeddings

`/v1/embeddings` should always normalize incoming input into a list and treat each item as an independent embedding task.

Policy:

- One input item maps to one upstream Vertex embedding call
- Response must contain exactly one embedding object per input item
- Original input order must be preserved in the `data[index]` response
- Partial success is not allowed
- Any single-item failure fails the entire request

This means the proxy should not attempt implicit true-batch embedding for Gemini embedding models unless there is model-specific proof that a single request returns multiple independent vectors with stable ordering.

### LLM

`/v1/chat/completions` should keep a simple one-request-to-one-upstream-call model.

Policy:

- One incoming OpenAI-compatible chat request maps to one upstream Vertex chat request
- No synthetic batch request format in v1
- Stream and non-stream responses should remain separate execution paths
- Performance tuning should focus on request concurrency and timeout control, not prompt batching

## Concurrency Policy

The proxy should support bounded concurrency rather than unbounded fan-out.

Recommended controls:

- `EMBEDDING_MAX_CONCURRENCY`
- `EMBEDDING_MAX_INPUTS_PER_REQUEST`
- `REQUEST_TIMEOUT_SECONDS`
- `EMBEDDING_RETRY_ATTEMPTS`
- `EMBEDDING_RETRY_BACKOFF_MS`
- `CHAT_RETRY_ATTEMPTS`
- `CHAT_RETRY_BACKOFF_MS`
- optional `GLOBAL_MAX_CONCURRENCY`

Recommended defaults:

- `EMBEDDING_MAX_CONCURRENCY=4`
- `EMBEDDING_MAX_INPUTS_PER_REQUEST=64`
- `REQUEST_TIMEOUT_SECONDS=60`
- `EMBEDDING_RETRY_ATTEMPTS=1`
- `CHAT_RETRY_ATTEMPTS=1`

## Failure Semantics

### Embeddings

Embeddings should follow an all-or-nothing contract.

If any single embedding item fails:

- return one request-level error
- do not return partial vectors
- do not reorder or drop successful vectors

Suggested status handling:

- `400/422` invalid input or unsupported model
- `429` upstream rate limiting
- `502` malformed upstream payload
- `503` auth, policy, or temporary upstream unavailability
- `504` timeout

### LLM

Chat requests should fail per request and should not synthesize a batch-level recovery model. Retries should be conservative and limited to retry-safe failures such as `429` and selected `5xx` responses.

## Throughput Strategy

Throughput improvements should not change request semantics.

Allowed:

- bounded async fan-out for embeddings
- small retry/backoff windows
- connection reuse
- global concurrency limits
- observability for input count, fan-out count, upstream latency, and status

Avoid in v1:

- implicit provider-specific embedding batch optimizations
- queue-backed asynchronous request semantics
- partial-success embedding responses
- synthetic LLM batch request handling

## Why This Policy Is Safe

This design avoids assuming that provider-specific multi-part input means multi-vector output. It keeps the OpenAI response contract deterministic and makes operational behavior understandable under rate limits, NAT pressure, or policy blockers.

## Suggested Next Implementation Steps

1. Add bounded concurrency for embedding fan-out using `asyncio.Semaphore`
2. Add `EMBEDDING_MAX_INPUTS_PER_REQUEST`
3. Add retry/backoff policy for `429` and retry-safe `5xx`
4. Add metrics/log fields for `input_count`, `fanout_count`, and retry attempts
5. Document the all-or-nothing embeddings contract in compatibility docs

