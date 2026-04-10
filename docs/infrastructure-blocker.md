# Infrastructure Blocker

## Current GKE Failure

In a namespace that runs both `vertex-openai-proxy` and another OpenAI-compatible gateway, both currently fail to mint a Vertex access token from inside the pod.

Observed runtime symptom:
- STS / metadata token exchange returns `403 Forbidden`
- error text includes `Request is prohibited by organization's policy`
- error text includes `vpcServiceControlsUniqueIdentifier`

This strongly suggests a VPC Service Controls or related org policy blocker, not an application bug.

## Reproduction

Run from an ops host against a pod in the affected namespace:

```bash
kubectl exec -n <namespace> <pod> -- python -c "
import httpx
r=httpx.get(
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
  headers={'Metadata-Flavor':'Google'},
  timeout=20.0,
)
print(r.status_code)
print(r.text[:1200])
"
```

Expected failing pattern:
- `403`
- `organization's policy`
- `vpcServiceControlsUniqueIdentifier=...`

## What To Ask The Platform Team

- verify the KSA to GSA mapping still exists for the affected workload service account
- verify `roles/iam.workloadIdentityUser` still exists on the mapped GSA
- inspect VPC Service Controls and org policy changes around the time failures started
- use the captured `vpcServiceControlsUniqueIdentifier` to find the exact denial event in Cloud Logging

## Decision Rule

- `mock/local` pass + `vm direct` pass + `in-cluster` fail:
  - treat as infrastructure blocker
- `mock/local` fail:
  - treat as code issue
- `vm direct` fail:
  - investigate proxy implementation or VM auth separately
