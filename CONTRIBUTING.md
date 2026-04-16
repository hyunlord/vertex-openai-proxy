# Contributing

Thanks for contributing to `vertex-openai-proxy`.

This project is intentionally narrow: it is a Vertex AI on GKE reference proxy
with a focused OpenAI-compatible surface. Contributions should preserve that
scope and avoid turning the project into a generic multi-provider gateway unless
the maintainer explicitly decides to expand the charter.

## Project Priorities

When in doubt, optimize in this order:

1. keep the public repository safe to use and redistribute
2. keep the reference deployment path stable for real GKE / GenOS serving
3. improve operational safety and compatibility without widening scope too fast

## Local Setup

Runtime-only install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Development and verification install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Copy the example environment and set a non-default token before running the app:

```bash
cp .env.example .env
```

## Verification Expectations

Before opening a PR, run:

```bash
python3 -m pytest tests -q
bash scripts/verify_quick.sh
bash scripts/verify_full.sh
bash scripts/verify_cross.sh
helm lint ./charts/vertex-openai-proxy --set auth.internalBearerToken=ci-smoke-token
helm template vertex-openai-proxy ./charts/vertex-openai-proxy --set auth.internalBearerToken=ci-smoke-token
```

If you touch Helm behavior, also validate the example values files under
[`charts/vertex-openai-proxy/examples`](/Users/rexxa/github/vertex-openai-proxy/charts/vertex-openai-proxy/examples).

## Scope Guidance

Good fits:

- Vertex-specific runtime reliability improvements
- clearer OpenAI-compatible behavior within the current scope
- documentation, release, and operator experience improvements
- tests that tighten compatibility or operational guarantees

Needs discussion first:

- multi-provider routing
- Assistants / Responses / Batch API support
- large config surface expansions
- changes that alter the current failure semantics for chat or embeddings

## Pull Requests

Please keep PRs:

- small enough to review in one sitting
- focused on one problem or one milestone step
- explicit about operator-visible behavior changes

In the PR description, include:

- what changed
- why it changed
- how it was verified
- rollout or rollback notes if the change affects live serving behavior

## Security

Do not commit:

- real bearer tokens
- service account keys
- private cluster names, internal hostnames, or environment-specific secrets

Use placeholders and public-safe examples in docs, manifests, and scripts.
