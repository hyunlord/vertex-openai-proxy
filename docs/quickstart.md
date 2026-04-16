# Quickstart

This guide is the shortest path to a working `vertex-openai-proxy` setup.

Use it when you want to:
- run the proxy locally against Vertex AI
- validate the proxy from a VM
- install the Helm chart on GKE

If you are operating a live rollout, use [runbook.md](runbook.md) and [canary-checklist.md](canary-checklist.md) after this guide.

## 1. Local Development Setup

Create a virtual environment and install both runtime and development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Copy the example environment file:

```bash
cp .env.example .env
```

At minimum, set:

```bash
export INTERNAL_BEARER_TOKEN=replace-with-a-random-token
export VERTEX_PROJECT_ID=your-gcp-project-id
export VERTEX_CHAT_LOCATION=global
export VERTEX_EMBEDDING_LOCATION=us-central1
export VERTEX_CHAT_MODEL=google/gemini-2.5-flash
export VERTEX_EMBEDDING_MODEL=gemini-embedding-2-preview
```

Run the server:

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Basic verification:

```bash
curl -s http://127.0.0.1:8080/health
PYTHONPATH=. python3 -m pytest tests -q
```

## 2. VM Direct Validation

Use this when GKE pod-to-Vertex auth is blocked but a VM can still call Vertex AI.

Build and run the container:

```bash
docker build -t vertex-openai-proxy:local .
docker run --rm -p 8080:8080 \
  -e INTERNAL_BEARER_TOKEN=replace-with-a-random-token \
  -e VERTEX_PROJECT_ID=your-gcp-project-id \
  -e VERTEX_CHAT_LOCATION=global \
  -e VERTEX_EMBEDDING_LOCATION=us-central1 \
  -e VERTEX_CHAT_MODEL=google/gemini-2.5-flash \
  -e VERTEX_EMBEDDING_MODEL=gemini-embedding-2-preview \
  vertex-openai-proxy:local
```

Then run the smoke path:

```bash
export PROXY_BASE_URL=http://127.0.0.1:8080
export INTERNAL_BEARER_TOKEN=replace-with-a-random-token
python3 scripts/smoke_vm_direct.py
```

## 3. Helm Install On GKE

For a minimal install:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set image.repository=your-registry/vertex-openai-proxy \
  --set image.tag=latest \
  --set auth.internalBearerToken=replace-with-a-random-token \
  --set config.vertexProjectId=your-gcp-project-id
```

If you already manage the bearer token in a Kubernetes secret:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set auth.existingSecret=vertex-openai-proxy-auth \
  --set auth.existingSecretKey=internal-bearer-token
```

For a production-style example, start from:

```bash
cat charts/vertex-openai-proxy/examples/values-production.yaml
```

Optional HPA:

```bash
helm upgrade --install vertex-openai-proxy ./charts/vertex-openai-proxy \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=6
```

Recommended Helm verification when `helm` is available:

```bash
helm lint ./charts/vertex-openai-proxy
helm template vertex-openai-proxy ./charts/vertex-openai-proxy
```

## 4. Multi-Model Example

To expose multiple chat models while keeping embeddings single-model:

```bash
export VERTEX_CHAT_MODEL=google/gemini-3.1-flash-lite-preview
export VERTEX_CHAT_MODELS=google/gemini-3.1-pro-preview
export VERTEX_CHAT_MODEL_ALIASES=genos-flash=google/gemini-3.1-flash-lite-preview,genos-pro=google/gemini-3.1-pro-preview
export VERTEX_EMBEDDING_MODEL=gemini-embedding-2-preview
```

## 5. What To Read Next

- [compatibility.md](compatibility.md) for the supported OpenAI surface
- [runbook.md](runbook.md) for rollout and rollback
- [canary-checklist.md](canary-checklist.md) for live verification
- [operations-transition.md](operations-transition.md) for VM-direct versus in-cluster validation
