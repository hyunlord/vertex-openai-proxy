# Private Infra Handoff

## Purpose

This repository should produce release artifacts and operator-facing guidance. It should not directly deploy to a private cloud environment.

Use this document when handing the public release to a private infrastructure repository or deployment system.

## Recommended Boundary

Keep these pieces in the public repository:

- source code
- tests and verification harness
- Helm chart
- example values
- changelog and release notes
- Docker build recipe
- public-safe release workflow

Move these pieces to a private infrastructure repository:

- cluster-specific Helm values
- private registry coordinates
- `INTERNAL_BEARER_TOKEN` secret management
- Workload Identity annotations and service account names
- Argo CD, Flux, or Helm release objects
- private DNS, ingress, and network policy configuration
- environment-specific alert routing

## What The Public Release Produces

The public-safe release workflow produces:

- a verified source release
- a packaged Helm chart
- an optional public container image published to `ghcr.io`

It does not:

- run `kubectl`
- run `helm upgrade`
- call `gcloud`
- target any specific cluster

## Inputs The Private Infra Layer Should Consume

The private deployment layer should consume:

- the Git tag, for example `v0.1.0`
- the GitHub Release assets
- the Helm chart package
- the container image tag or digest

Recommended handoff data:

- release tag
- image repository
- image digest
- chart version
- app version

## Private Repository Responsibilities

The private infrastructure repository should own:

- environment-specific `values.yaml`
- secret references for `INTERNAL_BEARER_TOKEN`
- Vertex project and model configuration
- Workload Identity and IAM binding
- rollout approval and rollback approval
- production alert routing and dashboards

## Suggested Deployment Shapes

Any of these are reasonable:

- Argo CD application that pins a chart version and image tag
- Flux HelmRelease that tracks a reviewed chart package
- internal Helm pipeline that promotes a release tag after approval

The key rule is that the private system should pull from this repository's release artifacts, not the other way around.

## Minimum Production Overrides

At minimum, private deployment values should override:

- `image.repository`
- `image.tag`
- `auth.existingSecret`
- `auth.existingSecretKey`
- `config.vertexProjectId`
- service account or Workload Identity annotations

## Security Notes

- never store `INTERNAL_BEARER_TOKEN` in the public repository
- keep private registry credentials outside this repository
- keep cluster names, project IDs, and internal hostnames out of the public repository

## Operational Notes

Use the public docs for operator guidance:

- [`docs/runbook.md`](runbook.md)
- [`docs/alerts.md`](alerts.md)
- [`docs/release.md`](release.md)
- [`docs/canary-checklist.md`](canary-checklist.md)

Use the private repository for:

- environment-specific rollout procedures
- environment-specific rollback approvals
- per-cluster scaling and alert thresholds

Private repo starter values can begin from these public-safe examples:

- [`examples/private-infra/values-common.yaml`](../examples/private-infra/values-common.yaml)
- [`examples/private-infra/values-canary.yaml`](../examples/private-infra/values-canary.yaml)
- [`examples/private-infra/values-stable.yaml`](../examples/private-infra/values-stable.yaml)
