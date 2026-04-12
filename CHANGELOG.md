# Changelog

All notable changes to `vertex-openai-proxy` should be recorded in this file.

The format is intentionally lightweight and keeps the newest release information near the top.

## Unreleased

### Added

- bounded request queueing for short burst smoothing
- Helm deployment profiles and example values
- service-wide adaptive runtime, observability, and overload protection
- Helm chart, optional `ServiceMonitor`, and Grafana dashboard asset

### Changed

- release validation now includes cross-boundary checks and Helm chart validation in CI
- infrastructure blocker guidance was consolidated into troubleshooting and release docs

## 0.1.0

### Added

- initial public release of the reference OpenAI-compatible proxy for Vertex AI
- OpenAI-style chat and embeddings endpoints
- SSE chat streaming
- model allowlist and compatibility surface docs
- harness verification scripts and protocol checks
