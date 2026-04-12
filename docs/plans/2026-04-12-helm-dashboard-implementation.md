# Helm And Dashboard Implementation Plan

## Objective

Implement a generic Helm chart and a Grafana dashboard for `vertex-openai-proxy` without adding
project-specific assumptions.

## Milestones

1. chart scaffold
2. values to env mapping
3. optional ServiceMonitor
4. Grafana dashboard JSON
5. docs updates
6. verification notes

## Task Breakdown

### Task 1: Create chart scaffold

Files:

- `charts/vertex-openai-proxy/Chart.yaml`
- `charts/vertex-openai-proxy/values.yaml`
- `charts/vertex-openai-proxy/templates/_helpers.tpl`

Changes:

- define chart metadata
- define reusable naming helpers
- provide structured default values

### Task 2: Add app deployment templates

Files:

- `charts/vertex-openai-proxy/templates/deployment.yaml`
- `charts/vertex-openai-proxy/templates/service.yaml`
- `charts/vertex-openai-proxy/templates/serviceaccount.yaml`
- `charts/vertex-openai-proxy/templates/configmap.yaml`
- `charts/vertex-openai-proxy/templates/secret.yaml`

Changes:

- map runtime values to environment variables
- wire probes to `/livez` and `/readyz`
- support either inline secret creation or existing secret usage

### Task 3: Add optional ServiceMonitor

Files:

- `charts/vertex-openai-proxy/templates/servicemonitor.yaml`

Changes:

- create only when enabled
- point to `/metrics`
- allow labels and scrape timing overrides

### Task 4: Add dashboard JSON

Files:

- `dashboards/vertex-openai-proxy-overview.json`

Changes:

- add runtime, request, latency, retry, concurrency, CPU/RSS, and shed panels

### Task 5: Update docs

Files:

- `README.md`

Changes:

- add Helm install examples
- add values override examples
- add dashboard import notes

## Verification

- run repository tests
- run harness quick/full verification
- if `helm` is available, run `helm lint` and `helm template`
- otherwise keep verification instructions in docs

## Guardrails

- keep the chart generic
- do not embed cluster-specific labels or namespaces
- do not reference private registries or secrets
