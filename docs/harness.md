# Harness

## Purpose

The harness layer exists to verify `vertex-openai-proxy` with explicit mechanical, protocol, and cross-LLM boundaries.

## Verification Layers

- mechanical checks
- protocol contract checks
- cross-LLM review boundary

## Local Usage

- `bash scripts/verify_quick.sh`
- `bash scripts/verify_full.sh`
- `bash scripts/verify_cross.sh`

## Information Isolation

Retry payloads expose only actionable issues and suggestions. Hidden score and verdict fields are removed before a coder retry payload is generated.
