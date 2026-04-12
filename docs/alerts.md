# Alerts

## Goal

These alerts are a practical starting set for `vertex-openai-proxy`. Tune thresholds after observing real traffic and runtime mode behavior in your environment.

## Recommended SLO Starting Point

- availability: `99.9%` successful proxy responses for healthy upstream conditions
- chat p95 latency: under `6000ms`
- embeddings p95 latency: under `4000ms` in steady state
- request shedding: near `0` during normal operation

## Alert Set

### Runtime Degraded

Severity: `critical`

Trigger when the service stays degraded for multiple evaluation windows.

Example:

```promql
max_over_time(vertex_proxy_runtime_mode{mode="degraded"}[5m]) > 0
```

### Runtime Not Ready

Severity: `critical`

Trigger when the runtime stays unready.

Example:

```promql
min_over_time(vertex_proxy_runtime_ready[5m]) < 1
```

### Request Shedding Active

Severity: `warning`

Trigger when overload protection starts rejecting requests.

Example:

```promql
increase(vertex_proxy_request_shed_total[5m]) > 0
```

### Queue Timeouts Rising

Severity: `warning`

Trigger when bounded queueing is no longer smoothing bursts and starts timing out.

Example:

```promql
increase(vertex_proxy_queue_timeouts_total[10m]) > 0
```

### Global Retryable Error Rate High

Severity: `warning`

Trigger when upstream retry-safe failures stay above the soft threshold.

Example:

```promql
vertex_proxy_retryable_error_rate{scope="global"} > 0.02
```

### Global Timeout Rate High

Severity: `warning`

Trigger when request timeouts exceed the normal operating budget.

Example:

```promql
vertex_proxy_timeout_rate{scope="global"} > 0.01
```

### Chat Latency High

Severity: `warning`

Trigger when chat p95 rises above the soft runtime threshold.

Example:

```promql
vertex_proxy_request_p95_latency_ms{scope="chat"} > 6000
```

### Embeddings Latency High

Severity: `warning`

Trigger when embeddings p95 rises above the soft runtime threshold.

Example:

```promql
vertex_proxy_request_p95_latency_ms{scope="embeddings"} > 4000
```

### Process Memory Pressure

Severity: `warning`

Trigger when process RSS approaches the configured runtime hard limit.

Example:

```promql
vertex_proxy_process_rss_mb > 900
```

### Process CPU Pressure

Severity: `warning`

Trigger when the proxy spends sustained time near CPU saturation.

Example:

```promql
vertex_proxy_process_cpu_percent > 85
```

## Dashboard Pairing

Correlate alerts with:

- `vertex_proxy_runtime_mode`
- `vertex_proxy_runtime_mode_transitions_total`
- `vertex_proxy_request_shed_total`
- `vertex_proxy_request_p95_latency_ms`
- `vertex_proxy_in_flight_requests`
- `vertex_proxy_queue_depth`
- `vertex_proxy_process_rss_mb`
- `vertex_proxy_process_cpu_percent`

## Tuning Guidance

- if runtime degraded alerts flap, lengthen the evaluation window before raising thresholds
- if request shedding is frequent, scale replicas before raising pod size
- if embeddings latency drives most alerts, review `EMBEDDING_MAX_CONCURRENCY` and batch behavior first
- if readiness alerts fire during controlled degradation, decide whether `READINESS_FAIL_ON_DEGRADED` is too aggressive for your replica count
