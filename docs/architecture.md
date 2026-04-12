# Architecture

`vertex-openai-proxy` is a single FastAPI service with a deliberately narrow responsibility: accept a small OpenAI-style HTTP surface and translate it into Vertex AI calls with predictable contracts.

## Components

- `app/routes/*`
  - HTTP entrypoints and internal bearer authentication
- `app/vertex_auth.py`
  - Vertex access token resolution through Workload Identity, metadata, or static override
- `app/services/vertex_chat.py`
  - chat request normalization, non-streaming translation, and SSE chunk relay
- `app/services/vertex_embeddings.py`
  - embeddings fan-out, response normalization, and failure semantics
- `app/model_registry.py`
  - allowlisted models and simple capabilities
- `app/errors.py`
  - OpenAI-style error envelopes
- `app/utils/logging.py`
  - request correlation and structured logging

## Request Flow

1. Client calls the proxy with a fixed internal bearer token.
2. The proxy validates the internal token.
3. Request middleware assigns a request id and stores it in request state and logging context.
4. The route validates the payload and model allowlist.
5. The service layer acquires a Vertex access token and calls the upstream Vertex endpoint.
6. The proxy normalizes the response into an OpenAI-compatible shape.
7. The response returns with `x-request-id`.

## Chat Flow

- Non-streaming chat:
  - request enters `/v1/chat/completions`
  - upstream call goes to Vertex OpenAI-compatible `chat/completions`
  - response is normalized to `chat.completion`
- Streaming chat:
  - request enters `/v1/chat/completions` with `stream=true`
  - upstream stream is consumed line-by-line
  - chunks are normalized to `chat.completion.chunk`
  - stream terminates with `data: [DONE]`

## Embeddings Flow

- request enters `/v1/embeddings`
- input is normalized to a list
- optional bounded queueing can briefly delay admission during short bursts
- proxy performs one upstream Vertex call per input item
- `asyncio.gather()` preserves order across fan-out responses
- fixed mode uses `EMBEDDING_MAX_CONCURRENCY`
- optional adaptive mode can raise or lower the effective concurrency step-by-step based on recent request health
- response is returned as OpenAI-style `data[index]`

## Design Principles

- keep the API surface small and explicit
- prefer deterministic failure over partial success
- keep queueing short, bounded, and optional
- never require long-lived Google API keys in GKE
- avoid leaking prompt or embedding content into logs
- enforce compatibility with tests, not documentation alone
- keep adaptive behavior optional, observable, and disabled by default

## Ongoing Validation Record

Live model and runtime tuning observations should be recorded in [empirical-testing.md](empirical-testing.md). Treat that file as the canonical append-only history for direct Vertex and end-to-end proxy experiments.
