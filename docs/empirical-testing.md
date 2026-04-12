# Empirical Testing Log

This document is the canonical running log for real-world model and proxy experiments.

Use it when:
- validating Vertex model behavior directly
- validating the proxy end-to-end against live Vertex APIs
- comparing runtime tuning choices such as embedding concurrency, retries, or request sizing

Rules:
- append new experiment rounds instead of replacing prior observations
- keep entries generic and reusable
- do not include customer names, internal hostnames, private service URLs, or secret material
- summarize what changed in code only after the behavior is observed here

## How To Use This Log

For every new experiment round, add:
- date
- environment type
- models tested
- request shapes
- observed results
- conclusions
- follow-up actions

Recommended sections per round:
- `Context`
- `Experiment Matrix`
- `Results`
- `Interpretation`
- `Next Changes`

## Canonical Reference

If future testing is requested, update this file first and then point other documentation or summaries back here.

## 2026-04-11 Round 1: Direct Vertex And Local Proxy Baseline

### Context

Goal:
- verify real behavior of `google/gemini-2.5-flash`
- verify real behavior of `gemini-embedding-2-preview`
- compare proxy embedding concurrency values while preserving one-input-to-one-upstream-call semantics

Environment types:
- `direct_vertex_local`: direct HTTPS requests to Vertex AI using a locally minted access token
- `proxy_local_vertex`: local `vertex-openai-proxy` process using a pre-minted Vertex token

### Experiment Matrix

| Environment | Model | Request shape | Runtime setting |
|---|---|---|---|
| `direct_vertex_local` | `google/gemini-2.5-flash` | single chat request | n/a |
| `direct_vertex_local` | `google/gemini-2.5-flash` | 3 concurrent chat requests | n/a |
| `direct_vertex_local` | `gemini-embedding-2-preview` | single embedding input | n/a |
| `direct_vertex_local` | `gemini-embedding-2-preview` | one request with 2 text parts | n/a |
| `direct_vertex_local` | `gemini-embedding-2-preview` | 8 concurrent single-input embedding requests | n/a |
| `proxy_local_vertex` | `google/gemini-2.5-flash` | single chat request | `EMBEDDING_MAX_CONCURRENCY=1,4,8` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | OpenAI `/v1/embeddings` with 8 inputs | `EMBEDDING_MAX_CONCURRENCY=1,4,8` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | OpenAI `/v1/embeddings` with 16 inputs | `EMBEDDING_MAX_CONCURRENCY=1,4,8` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | OpenAI `/v1/embeddings` with 32 inputs | `EMBEDDING_MAX_CONCURRENCY=4,8` |

### Results

#### Direct Vertex

| Scenario | Status | Latency | Notes |
|---|---:|---:|---|
| chat single | `200` | `1315.8ms` | response content was `READY` |
| chat concurrent 3 | `200 x 3` | `890.5ms` to `962.3ms` | all responses returned `READY` |
| embedding single | `200` | `1851.9ms` | vector length `3072` |
| embedding multipart 2 parts | `200` | `648.3ms` | returned one embedding object with vector length `3072` |
| embedding concurrent 8 | `200 x 8` | `969.1ms` to `1982.8ms` | all vectors length `3072` |

#### Local Proxy Against Vertex

| Concurrency | Input count | Status | Latency | Output |
|---|---:|---:|---:|---|
| `1` | `8` | `200` | `14094.3ms` | `data_count=8`, vector length `3072` |
| `1` | `16` | `200` | `26830.9ms` | `data_count=16`, vector length `3072` |
| `4` | `8` | `200` | `3678.1ms` | `data_count=8`, vector length `3072` |
| `4` | `16` | `200` | `7402.4ms` | `data_count=16`, vector length `3072` |
| `4` | `32` | `200` | `14030.7ms` | `data_count=32`, vector length `3072` |
| `8` | `8` | `200` | `1949.1ms` | `data_count=8`, vector length `3072` |
| `8` | `16` | `200` | `3850.6ms` | `data_count=16`, vector length `3072` |
| `8` | `32` | `200` | `7293.3ms` | `data_count=32`, vector length `3072` |

Chat through the local proxy remained healthy across these runs:
- typical single-request latency was roughly `832ms` to `1635ms`
- responses remained correct

### Interpretation

- `gemini-embedding-2-preview` should not be treated as a true multi-vector batch endpoint based on `parts`
- one input item must remain one upstream embedding call
- bounded concurrency materially improves throughput without changing correctness
- `EMBEDDING_MAX_CONCURRENCY=1` is too conservative for realistic batch sizes
- `EMBEDDING_MAX_CONCURRENCY=4` is a safe default
- `EMBEDDING_MAX_CONCURRENCY=8` is a strong tuning candidate for higher-ingestion environments

### Next Changes

- keep code default at `EMBEDDING_MAX_CONCURRENCY=4`
- document `8` as an operator tuning starting point for heavier ingestion workloads
- run a future round covering:
  - concurrency `12` and `16`
  - input count `64`
  - multiple concurrent `/v1/embeddings` requests
  - retry-path timing under synthetic `429/503`

## 2026-04-11 Round 2: Higher Concurrency, Larger Inputs, And Gemini 3 Variants

### Context

Goal:
- extend embedding tests to concurrency `12` and `16`
- test larger input sizes `32` and `64`
- test multiple concurrent embedding requests
- compare additional Gemini chat models for availability, latency, rough quality, and estimated cost

Pricing reference:
- Vertex AI pricing page for Gemini on Vertex AI
- costs below are estimated from response `usage` fields and public on-demand pricing, not billing exports

### Experiment Matrix

| Environment | Model | Request shape | Runtime setting |
|---|---|---|---|
| `proxy_local_vertex` | `gemini-embedding-2-preview` | `/v1/embeddings` with 32 inputs | `EMBEDDING_MAX_CONCURRENCY=12` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | `/v1/embeddings` with 64 inputs | `EMBEDDING_MAX_CONCURRENCY=12` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 3 concurrent requests, each with 16 inputs | `EMBEDDING_MAX_CONCURRENCY=12` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | `/v1/embeddings` with 32 inputs | `EMBEDDING_MAX_CONCURRENCY=16` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | `/v1/embeddings` with 64 inputs | `EMBEDDING_MAX_CONCURRENCY=16` |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 3 concurrent requests, each with 16 inputs | `EMBEDDING_MAX_CONCURRENCY=16` |
| `direct_vertex_local` | `google/gemini-3-flash-preview` | short chat prompts | n/a |
| `direct_vertex_local` | `google/gemini-3.1-pro-preview` | short chat prompts | n/a |
| `direct_vertex_local` | `google/gemini-3.1-flash-preview` | availability check | n/a |

### Results

#### Proxy Embeddings: Concurrency 12

| Scenario | Status | Latency | Notes |
|---|---:|---:|---|
| 32 inputs | `200` | `4416.8ms` | `data_count=32`, vector length `3072` |
| 64 inputs | `200` | `9541.2ms` | `data_count=64`, vector length `3072` |
| 3 concurrent requests x 16 inputs | `200 x 3` | `2956.6ms` to `3740.6ms` | wall time `3773.4ms` |

#### Proxy Embeddings: Concurrency 16

| Scenario | Status | Latency | Notes |
|---|---:|---:|---|
| 32 inputs | `200` | `3688.3ms` | `data_count=32`, vector length `3072` |
| 64 inputs | `200` | `6240.0ms` | `data_count=64`, vector length `3072` |
| 3 concurrent requests x 16 inputs | `200 x 3` | `2003.8ms` to `2106.0ms` | wall time `2136.6ms` |

#### Gemini Chat Model Availability And Quality Snapshot

Availability checks:
- `google/gemini-3-flash-preview`: available
- `google/gemini-3.1-pro-preview`: available
- `google/gemini-3.1-flash-preview`: returned `404`
- `google/gemini-3-pro-preview`: returned `404`

Prompt quality/cost snapshot:

| Model | Case | Status | Latency | Output quality | Estimated cost |
|---|---|---:|---:|---|---:|
| `google/gemini-2.5-flash` | obedience | `200` | `871.6ms` | exact `READY` | `$0.0000040` |
| `google/gemini-2.5-flash` | reasoning | `200` | `1685.5ms` | correct `323` | `$0.0000123` |
| `google/gemini-2.5-flash` | systems | `200` | `3247.6ms` | correct, fuller sentence | `$0.0000661` |
| `google/gemini-3-flash-preview` | obedience | `200` | `1716.5ms` | exact `READY` | `$0.0000055` |
| `google/gemini-3-flash-preview` | reasoning | `200` | `1976.1ms` | correct `323` | `$0.0000170` |
| `google/gemini-3-flash-preview` | systems | `200` | `2880.0ms` | correct, concise | `$0.0000570` |
| `google/gemini-3.1-pro-preview` | obedience | `200` | `4280.9ms` | exact `READY` | `$0.0000220` |
| `google/gemini-3.1-pro-preview` | reasoning | `200` | `3205.9ms` | correct `323` | `$0.0000680` |
| `google/gemini-3.1-pro-preview` | systems | `200` | `6966.5ms` | correct, polished | `$0.0003000` |

### Interpretation

- `EMBEDDING_MAX_CONCURRENCY=12` is stable in this environment and substantially better than `8`
- `EMBEDDING_MAX_CONCURRENCY=16` is also stable in this environment and materially better than `12`
- no correctness regression was observed at higher embedding concurrency; output counts and vector lengths remained correct
- based on current evidence, higher embedding concurrency changes throughput much more than it changes chat latency
- `google/gemini-3-flash-preview` is available and behaves as a practical faster/cheaper higher-generation option than `3.1-pro`
- `google/gemini-3.1-pro-preview` is available and cost is still trivial for tiny prompts, but latency and per-call cost are noticeably higher
- `google/gemini-3.1-flash-preview` was not available to this project at test time

### Next Changes

- keep the proxy contract unchanged: one input item still maps to one upstream embedding call
- do not infer that all projects can safely run concurrency `16`; this was only one environment
- consider updating operator guidance to:
  - start at `8`
  - evaluate `12`
  - use `16` only after confirming quota, NAT, and tail latency in the target environment
- future rounds should cover:
  - retry-path latency under synthetic `429/503`
  - mixed chat + embeddings load
  - more realistic quality prompts for `google/gemini-3-flash-preview` vs `google/gemini-3.1-pro-preview`

## 2026-04-12 Round 3: Adaptive Embedding Concurrency Healthy-Path Validation

### Context

Goal:
- verify that the new optional adaptive embedding concurrency mode can scale up under healthy load
- confirm that response correctness remains unchanged while adaptive mode is active
- compare adaptive behavior against the same-day fixed concurrency baseline

Environment type:
- `proxy_local_vertex`

Configuration notes:
- adaptive mode enabled only for this experiment
- base fixed concurrency remained `4`
- adaptive max concurrency was `16`
- cooldown was reduced to `0` seconds for faster observation
- minimum samples was reduced to `3` for faster scale-up observation

These settings were chosen only to validate controller behavior quickly. They are not recommended
public defaults.

### Experiment Matrix

| Environment | Model | Request shape | Runtime setting |
|---|---|---|---|
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 3 sequential requests with 8 inputs | adaptive enabled |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 2 sequential requests with 16 inputs | adaptive enabled |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 1 sequential request with 32 inputs | adaptive enabled |
| `proxy_local_vertex` | `gemini-embedding-2-preview` | 1 sequential request with 32 inputs | adaptive disabled, fixed concurrency `4` |

### Results

#### Adaptive Enabled

| Input count | Status | Latency | Output |
|---|---:|---:|---|
| `8` | `200` | `3833.2ms` | `data_count=8` |
| `8` | `200` | `3689.6ms` | `data_count=8` |
| `8` | `200` | `3465.1ms` | `data_count=8` |
| `16` | `200` | `3676.7ms` | `data_count=16` |
| `16` | `200` | `3410.9ms` | `data_count=16` |
| `32` | `200` | `3681.8ms` | `data_count=32` |

#### Fixed Baseline

| Input count | Status | Latency | Output |
|---|---:|---:|---|
| `32` | `200` | `13181.5ms` | `data_count=32` |

### Interpretation

- adaptive mode preserved correctness: all responses stayed `200` and `data_count` always matched input count
- under healthy local conditions, the adaptive controller reduced `32`-input latency from `13181.5ms` to `3681.8ms`
- that improvement strongly suggests the controller scaled above the fixed starting point of `4`
- the gain was large enough to justify keeping adaptive mode as an optional operator feature
- the test still covered only the healthy path; no live retryable-failure or timeout downscale round has been recorded yet

### Next Changes

- keep adaptive mode disabled by default
- document adaptive mode as an advanced tuning option rather than a default behavior
- add a future round that validates fast scale-down under induced retryable failures or timeouts

## 2026-04-12 Round 4: Adaptive Scale-Down Under Synthetic Retryable Failures

### Context

Goal:
- verify that adaptive embedding concurrency backs off after retryable failures
- keep the experiment generic and deterministic by injecting retryable upstream failures in-process

Environment type:
- `proxy_in_process_synthetic`

Configuration notes:
- adaptive mode enabled
- base concurrency `4`
- adaptive max concurrency `16`
- cooldown `0` seconds
- minimum samples `3`
- embedding retries disabled to make each retryable failure immediately visible to the controller

### Experiment Matrix

| Environment | Model | Request shape | Runtime setting |
|---|---|---|---|
| `proxy_in_process_synthetic` | `gemini-embedding-2-preview` | 4 healthy embedding requests with 4 inputs each | adaptive enabled |
| `proxy_in_process_synthetic` | `gemini-embedding-2-preview` | 3 failing embedding requests with 4 inputs each, injected `503` | adaptive enabled |

### Results

| Phase | Step | Effective concurrency after request | Failure rate | Notes |
|---|---:|---:|---:|---|
| healthy | 1 | `4` | `0.0` | baseline initialization |
| healthy | 2 | `4` | `0.0` | still below scale-up trigger |
| healthy | 3 | `8` | `0.0` | first scale-up |
| healthy | 4 | `12` | `0.0` | second scale-up |
| failure | 1 | `8` | `0.20` | immediate downscale after first retryable failure |
| failure | 2 | `4` | `0.333...` | second downscale to base |
| failure | 3 | `4` | `0.428...` | stayed at base floor |

### Interpretation

- the controller scaled up under healthy request history
- retryable failures caused the controller to back off quickly
- the current ladder and thresholds behaved as intended in a deterministic synthetic scenario
- this confirms the controller can both scale up and scale down without changing embedding correctness semantics

### Next Changes

- add a future timeout-heavy round to confirm timeout-driven downscale behavior
- after more live evidence is collected, decide whether adaptive mode should remain operator-only or become a recommended optional setting

## 2026-04-12 Round 5: Live Runtime Mode And Metrics Validation

### Context

Goal:
- verify that the shared runtime controller can change service mode during live Vertex-backed requests
- confirm that `/health` and `/metrics` reflect the current runtime mode after a live request

Environment type:
- `proxy_local_vertex`

Configuration notes:
- runtime adaptive mode enabled
- service-level thresholds intentionally lowered for observation
- one elevated scenario and one degraded scenario were executed separately

### Experiment Matrix

| Scenario | Request shape | Soft embeddings latency threshold | Hard embeddings latency threshold |
|---|---|---:|---:|
| `elevated` | one `/v1/embeddings` request with 8 inputs | `1000ms` | `10000ms` |
| `degraded` | one `/v1/embeddings` request with 8 inputs | `1000ms` | `2000ms` |

### Results

| Scenario | Before `/health` mode | After `/health` mode | Status | Latency | Output | Metrics summary |
|---|---|---|---:|---:|---|---|
| `elevated` | `normal` | `elevated` | `200` | `3894.4ms` | `data_count=8` | `/metrics` reported `vertex_proxy_runtime_mode{mode="elevated"} 1` |
| `degraded` | `normal` | `degraded` | `200` | `3687.0ms` | `data_count=8` | `/metrics` reported `vertex_proxy_runtime_mode{mode="degraded"} 1` |

Observed metrics:

- elevated scenario:
  - `vertex_proxy_request_p95_latency_ms{scope="embeddings"} 3887.016`
- degraded scenario:
  - `vertex_proxy_request_p95_latency_ms{scope="embeddings"} 3680.034`

### Interpretation

- the shared runtime controller can drive service mode changes under live Vertex-backed traffic
- `/health` correctly surfaced the runtime mode after the request completed
- `/metrics` correctly reflected the active runtime mode and recent embeddings latency
- this makes the runtime controller operationally observable rather than implicit

### Next Changes

- add empirical runs that include multiple chat and embedding requests in the same window
- add future rounds covering recovery behavior from `degraded -> elevated -> normal`
