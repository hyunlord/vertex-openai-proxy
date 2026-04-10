# Release

## Expectations

- all tests pass
- `verify_quick.sh` passes
- `verify_full.sh` passes
- compatibility docs match the implementation
- VM direct validation path is documented and runnable

## Current Scope

- reference proxy verification
- harness mechanical and protocol gates
- pluggable cross-LLM boundary

## GKE Blocker Rule

If GKE requests fail with:
- `organization's policy`
- `vpcServiceControlsUniqueIdentifier`
- STS or metadata token exchange failures

do not treat that as an application regression by default.

Before release rollback or code changes, compare:
- local/mock verification
- VM direct verification
- in-cluster verification

If only `in-cluster` fails, classify it as an infrastructure blocker until proven otherwise.
