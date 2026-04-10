# Troubleshooting

## 401 Unauthorized

Likely causes:
- missing or incorrect `Authorization: Bearer <INTERNAL_BEARER_TOKEN>`
- internal bearer token configured differently between client and proxy

Check:
- proxy environment variable `INTERNAL_BEARER_TOKEN`
- client bearer token value

## 403 Permission Denied

Likely causes:
- GKE Workload Identity mapping is missing or incorrect
- mapped Google service account lacks Vertex prediction permissions
- STS token exchange is denied by VPC Service Controls or a related org policy

Check:
- Kubernetes service account to Google service account annotation
- Vertex IAM roles on the mapped Google service account
- whether the error includes `organization's policy`
- whether the error includes `vpcServiceControlsUniqueIdentifier`

If the proxy returns a message mentioning:
- `auth_path=adc->metadata`
- `organization's policy`
- `vpcServiceControlsUniqueIdentifier=...`

then the failure is very likely outside the application code. In that case:
- compare the same request in `vm direct` mode
- capture the `vpcServiceControlsUniqueIdentifier`
- ask the platform team to inspect Cloud Logging for the related STS / VPC SC denial

## 404 Not Found

Likely causes:
- unsupported model id
- wrong Vertex location
- wrong project id

Check:
- `/v1/models`
- `VERTEX_PROJECT_ID`
- `VERTEX_CHAT_LOCATION`
- `VERTEX_EMBEDDING_LOCATION`

## 422 Invalid Request

Likely causes:
- malformed `messages`
- embedding input includes non-string items
- missing required fields

Check:
- request body shape
- list inputs contain only strings

## 429 Rate Limit

Likely causes:
- Vertex quota pressure
- too many concurrent upstream requests

Check:
- Vertex quota dashboards
- embeddings fan-out concurrency from calling workloads
- `EMBEDDING_MAX_CONCURRENCY`
- `EMBEDDING_MAX_INPUTS_PER_REQUEST`

The proxy intentionally uses one upstream embedding call per input item. Large client-side arrays can still generate many upstream calls, so tune proxy concurrency before increasing caller batch sizes.

## 502 Upstream / Malformed Payload

Likely causes:
- upstream Vertex returned a malformed response
- embedding payload missing `embedding.values`
- streaming path returned invalid JSON chunks
- authentication succeeded but the Google API still failed upstream

Check:
- proxy logs with `x-request-id`
- structured log fields:
  - `operation`
  - `model`
  - `mode`
  - `upstream_status`
  - `upstream_latency_ms`

## Logging

The proxy logs structured request summaries with:
- `request_id`
- `operation`
- `endpoint`
- `model`
- `mode`
- `upstream_status`
- `upstream_latency_ms`

Embeddings also log:
- `input_count`
- `fanout_count`
- `retry_attempts`

Chat logs also include:
- `retry_attempts`

## GKE Fails But VM Direct Succeeds

Interpretation:
- the proxy implementation is probably correct
- the failure is likely in GKE auth, STS federation, VPC Service Controls, or org policy

Recommended evidence to collect:
- failing in-cluster request
- matching `x-request-id`
- exact error body
- `vpcServiceControlsUniqueIdentifier`
- the result of `python3 scripts/smoke_vm_direct.py` on the ops VM
