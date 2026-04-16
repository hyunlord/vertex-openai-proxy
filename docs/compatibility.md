# Compatibility

## Supported Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`

## Chat Completions

Supported request fields:
- `model`
- `messages`
- `stream`
- `tools`
- `tool_choice`

Chat model behavior:
- `model` may be omitted, in which case the configured default chat model is used
- `model` may be a configured alias such as `genos-flash`
- `model` may be a configured raw model ID such as `google/gemini-3.1-pro-preview`
- chat aliases resolve to a raw model ID before the Vertex upstream call is made

Supported response shapes:
- `chat.completion`
- `chat.completion.chunk`

Supported behavior:
- request validation for malformed messages
- `messages[].content` may be a plain string or an array of OpenAI-style `text` content parts
- text content parts are flattened into the existing Vertex string-based request shape
- non-stream tool-calling request passthrough
- assistant `tool_calls` normalization on non-stream responses
- `tool` role message passthrough on non-stream requests
- streaming tool-call chunk passthrough and normalization
- upstream stream failures emit one SSE `error` event and then terminate with `data: [DONE]`, both before the first chunk and mid-stream
- request id correlation via `x-request-id`
- normalized usage passthrough when Vertex provides usage
- SSE termination with `data: [DONE]`

Example clients:
- [`examples/curl/tool_calling.sh`](../examples/curl/tool_calling.sh)
- [`examples/python/tool_calling.py`](../examples/python/tool_calling.py)

Not supported yet:
- Responses API
- Assistants API
- image/audio/non-text content parts
- multimodal normalization beyond upstream passthrough surface

## Embeddings

Supported request fields:
- `model`
- `input`
- `user`
- `dimensions`

Supported input forms:
- single string
- list of strings

Contract guarantees:
- one output vector per input item
- preserved input order
- explicit indices in response data
- one upstream embedding call per input item
- bounded fan-out concurrency using proxy-side limits
- whole-request failure if any item fails
- `usage.prompt_tokens` and `usage.total_tokens` are split-based approximate counts, not exact tokenizer results
- malformed upstream embedding payloads return normalized `502`

Retry behavior:
- embeddings retry only on retry-safe upstream statuses
- non-stream chat retries only on retry-safe upstream statuses
- stream chat does not retry once streaming has started

## Errors

All handled errors return an OpenAI-style envelope:

```json
{
  "error": {
    "message": "...",
    "type": "invalid_request_error",
    "code": 422
  }
}
```

## Models

Only allowlisted models are supported. `/v1/models` returns the proxy's current allowlist rather than every model Vertex might support.

For chat models, the allowlist may include:
- configured raw model IDs
- configured aliases that map to those raw model IDs

Embeddings remain single-model for now even when chat is configured for multi-model use.
