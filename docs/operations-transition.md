# Operations Transition

## Goal

Move a client application from an existing OpenAI-compatible gateway to `vertex-openai-proxy` after GKE policy blockers are resolved.

## Required Inputs

- service URL for `vertex-openai-proxy`
- `INTERNAL_BEARER_TOKEN`
- chat model: `google/gemini-2.5-flash`
- embedding model: `gemini-embedding-2-preview`

## Runtime Expectations

- embeddings requests may contain multiple inputs, but the proxy will still issue one upstream embedding call per item
- embeddings are all-or-nothing; partial success is not returned
- throughput tuning should start with `EMBEDDING_MAX_CONCURRENCY`, not caller-side implicit batching assumptions
- non-stream chat may retry retry-safe failures; stream chat does not

## Revalidation Sequence

1. Confirm local/mock checks pass:
   - `python3 -m pytest tests -q`
   - `bash scripts/verify_quick.sh`
   - `bash scripts/verify_full.sh`
2. Confirm VM direct check passes:
   - `python3 scripts/smoke_vm_direct.py`
3. Re-test in GKE:
   - `python3 scripts/smoke_in_cluster.py`
4. Update the client application's external API configuration only after the four endpoints are verified in-cluster

## Rollback Rule

If GKE requests fail but VM direct remains healthy:
- rollback traffic changes only
- do not immediately rollback the application image
- capture STS / VPC SC evidence first
