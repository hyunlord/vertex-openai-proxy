# Helm And Dashboard Design

## Goal

Add packaging and observability artifacts that make `vertex-openai-proxy` easier to deploy and
monitor as a platform-oriented operational reference.

This round should provide:

- a reusable Helm chart for application deployment
- optional Prometheus Operator `ServiceMonitor` support
- a Grafana dashboard JSON file for the proxy's runtime and overload metrics

## Scope

The chart is intentionally app-focused.

Included:

- `Deployment`
- `Service`
- optional `ServiceAccount`
- `ConfigMap`
- optional `Secret`
- optional `ServiceMonitor`
- probes, resources, scheduling knobs, and runtime env mapping

Excluded:

- no bundled Prometheus stack
- no bundled Grafana deployment
- no cloud-specific manifests

## Design Summary

The chart will live under `charts/vertex-openai-proxy/`.

Values are grouped into:

- `app`
- `auth`
- `runtime`
- `prometheus`

This keeps operator-facing settings easy to discover while preserving a stable mapping to the
runtime environment variables already used by the application.

Grafana assets will live under `dashboards/`.

The first dashboard will be a single overview board showing:

- runtime mode
- readiness
- request volume and status class breakdown
- p95 latency by scope
- retryable error and timeout rates
- effective embedding concurrency
- process CPU and RSS
- request shedding counters

## Helm Approach Options

### 1. App-only chart

Pros:

- simplest
- least cluster coupling

Cons:

- operators still need to wire monitoring themselves

### 2. App chart with optional ServiceMonitor

Pros:

- portable by default
- integrates well in Prometheus Operator environments
- keeps monitoring integration close to the app

Cons:

- still requires a separate dashboard import step

### 3. App chart plus Grafana CRDs

Pros:

- convenient in some clusters

Cons:

- adds assumptions about installed operators
- reduces portability

The recommended approach is option 2.

## Values Structure

### App

- image repository, tag, pull policy
- replica count
- service port and type
- probes
- resources
- node selector, tolerations, affinity

### Auth

- `existingSecret`
- `existingSecretKey`
- fallback inline `internalBearerToken`
- optional inline `vertexAccessToken`

### Runtime

Map the application's generic runtime knobs into structured values:

- embedding concurrency and retries
- adaptive embedding controls
- service-wide adaptive runtime
- in-flight caps
- degraded-mode limits

### Prometheus

- `serviceMonitor.enabled`
- labels
- scrape interval
- scrape timeout

## Secrets Model

Operators may either:

- supply `auth.existingSecret`
- or let the chart create a secret from inline placeholder values

This preserves portability without forcing a specific secret management workflow.

## Probe Policy

- liveness uses `/livez`
- readiness uses `/readyz`

This matches the service's current operational semantics.

## Dashboard Design

The dashboard should be generic and importable without cluster-specific edits.

Panels:

1. current runtime mode
2. readiness state
3. request counts by scope and status class
4. p95 latency by scope
5. retryable error and timeout rates
6. effective embedding concurrency
7. process CPU and RSS
8. request shedding totals by endpoint and reason

## Documentation

README should gain:

- Helm install example
- values override example
- ServiceMonitor toggle example
- dashboard import guidance

## Guardrails

- no project-specific names, URLs, or cloud identifiers
- no hard dependency on Prometheus Operator
- no hard dependency on Grafana CRDs
- keep all defaults generic and conservative
