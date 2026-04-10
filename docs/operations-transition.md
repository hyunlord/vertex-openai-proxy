# Operations Transition

## Goal

Move a client application from an existing OpenAI-compatible gateway to `vertex-openai-proxy` after GKE policy blockers are resolved.

## Required Inputs

- service URL for `vertex-openai-proxy`
- `INTERNAL_BEARER_TOKEN`
- chat model: `google/gemini-2.5-flash`
- embedding model: `gemini-embedding-2-preview`

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
