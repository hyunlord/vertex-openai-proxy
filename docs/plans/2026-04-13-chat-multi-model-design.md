# Chat Multi-Model Design

**Goal**

Allow a single `vertex-openai-proxy` deployment to serve multiple chat models while keeping embeddings on a single configured model.

**Why**

Today the proxy exposes exactly one chat model and one embedding model. That forces operators to deploy multiple pods if they want both a fast chat model and a higher-quality chat model. We want one pod to handle multiple chat models so GenOS can choose between them without multiplying resource reservations.

## Scope

In scope:
- Multiple configured chat models in one proxy instance
- Support both alias names and raw Vertex model IDs in `model`
- Preserve one default chat model when `model` is omitted
- Keep embeddings single-model for now
- Return a richer `/v1/models` list showing the configured chat choices

Out of scope:
- Dynamic model registration at runtime
- Multi-model embeddings
- Per-model concurrency controls
- Admin APIs for model configuration

## Configuration

Introduce a registry-shaped chat configuration:

- `VERTEX_CHAT_MODEL`
  - Default chat model
- `VERTEX_CHAT_MODELS`
  - Optional comma-separated list of additional allowed chat models
- `VERTEX_CHAT_MODEL_ALIASES`
  - Optional comma-separated `alias=model-id` pairs

Example:

```env
VERTEX_CHAT_MODEL=google/gemini-3.1-flash-lite-preview
VERTEX_CHAT_MODELS=google/gemini-3.1-pro-preview
VERTEX_CHAT_MODEL_ALIASES=genos-flash=google/gemini-3.1-flash-lite-preview,genos-pro=google/gemini-3.1-pro-preview
```

Rules:
- The default chat model is always allowed.
- Additional chat models extend the allowed set.
- Aliases may point only to allowed chat models.
- Raw model IDs remain valid even when aliases exist.
- Embeddings continue using `VERTEX_EMBEDDING_MODEL`.

## Request Behavior

### Chat

- `model` becomes optional in the request schema.
- If `model` is omitted, use the default chat model.
- If `model` matches an alias, resolve it to the mapped Vertex model ID.
- If `model` matches a configured raw model ID, use it directly.
- Otherwise return `400 Unsupported chat model`.

The upstream Vertex call should always use the resolved raw model ID.
The normalized response should return the resolved raw model ID in the `model` field so logs and downstream debugging are unambiguous.

### Embeddings

- No behavior change for now.
- Keep current single-model logic.
- Refactor registry helpers so embeddings can adopt the same pattern later without a large rewrite.

## Registry Behavior

Split model registry responsibilities into explicit chat and embedding helpers:

- `resolve_chat_model(requested_model: str | None) -> str`
- `ensure_supported_chat_model(requested_model: str | None) -> str`
- `resolve_embedding_model(requested_model: str | None) -> str`
- `list_models()`

`/v1/models` should include:
- Alias entries
- Raw configured chat model entries
- The configured embedding model entry

Alias entries should identify their target model in metadata so operators can see what each alias resolves to.

## Logging and Observability

For chat requests:
- Admission logs should record the original requested model and the resolved model
- Completion logs should record the resolved model

This keeps GenOS-facing names visible without losing the actual upstream model used.

## Compatibility Impact

This change directly helps GenOS:
- Flowise or gateway callers can use stable aliases such as `genos-flash` and `genos-pro`
- Raw OpenAI-style callers can still pass full Vertex model IDs
- One deployment can cover the common chat model set without spawning separate pods

## Testing

Add tests for:
- Default chat model when `model` is omitted
- Alias resolution
- Raw model ID passthrough
- Unsupported chat model rejection
- `/v1/models` containing aliases and raw model entries
- Chat responses using resolved model IDs
- Embedding behavior remaining unchanged

## Rollout Notes

Initial rollout should configure:
- default chat model: `google/gemini-3.1-flash-lite-preview`
- secondary chat model: `google/gemini-3.1-pro-preview`
- embedding model: `gemini-embedding-2-preview`

Recommended aliases:
- `genos-flash`
- `genos-pro`
