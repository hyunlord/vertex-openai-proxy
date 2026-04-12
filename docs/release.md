# Release

## Expectations

- all tests pass
- `verify_quick.sh` passes
- `verify_full.sh` passes
- `verify_cross.sh` passes
- `helm lint ./charts/vertex-openai-proxy` passes
- `helm template vertex-openai-proxy ./charts/vertex-openai-proxy` passes
- compatibility docs match the implementation
- VM direct validation path is documented and runnable

## Current Scope

- reference proxy verification
- harness mechanical and protocol gates
- pluggable cross-LLM boundary
- Helm chart validation

## Local Release Commands

Run:

```bash
python3 -m pytest tests -q
bash scripts/verify_quick.sh
bash scripts/verify_full.sh
bash scripts/verify_cross.sh
helm lint ./charts/vertex-openai-proxy
helm template vertex-openai-proxy ./charts/vertex-openai-proxy
```

## Versioning Policy

- `app version` tracks the user-facing proxy release line
- `Chart version` tracks Helm packaging changes and should be updated whenever chart behavior or defaults change
- patch releases should cover bug fixes, docs corrections, and validation hardening
- minor releases should cover backward-compatible feature additions
- breaking compatibility changes should use a major version increment

Current chart metadata:

- Chart version: `0.1.0`
- app version: `0.1.0`

When preparing a release:

1. update [CHANGELOG.md](../CHANGELOG.md)
2. update `charts/vertex-openai-proxy/Chart.yaml` if the release changes chart or app version
3. make sure release notes match the changelog summary

## Release Note Template

Use this format for GitHub releases or public release summaries:

```markdown
## Summary

- short release description

## Added

- new feature or operator-visible capability

## Changed

- behavior changes or tuning changes

## Fixed

- bugs, regressions, or validation hardening

## Operational Notes

- deployment, chart, or runtime guidance

## Known Limitations

- environment blockers or intentionally unsupported surface
```

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

Typical escalation evidence:
- failing in-cluster request body or response summary
- `x-request-id`
- direct metadata token fetch result from inside the pod
- captured `vpcServiceControlsUniqueIdentifier`
