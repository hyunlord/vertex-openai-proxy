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

Supported response shapes:
- `chat.completion`
- `chat.completion.chunk`

Supported behavior:
- request validation for malformed messages
- request id correlation via `x-request-id`
- normalized usage passthrough when Vertex provides usage
- SSE termination with `data: [DONE]`

Not supported yet:
- tool calling compatibility
- Responses API
- Assistants API
- audio/image/multimodal normalization beyond upstream passthrough surface

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
- whole-request failure if any item fails
- malformed upstream embedding payloads return normalized `502`

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
