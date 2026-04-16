# Validation

This document collects the verification paths that go beyond the local quickstart.

Use it when you need to answer one of these questions:
- does the proxy work with mocked local checks?
- does a VM with working Vertex access prove the image is healthy?
- does the same image still work in-cluster with Workload Identity and perimeter policy?

## Validation Layers

The repository keeps three validation layers:

- `mock/local`
  - unit, contract, and harness checks without live Vertex access
- `vm direct`
  - run the proxy on a VM that can already call Vertex AI
- `in-cluster`
  - confirm the same request flow inside GKE with Workload Identity

If `mock/local` passes and `vm direct` passes but `in-cluster` fails, treat the issue as infrastructure first unless the app contract itself changed.

## Mock / Local

Primary local verification:

```bash
PYTHONPATH=. python3 -m pytest tests -q
bash scripts/verify_quick.sh
bash scripts/verify_full.sh
bash scripts/verify_cross.sh
```

This path covers:
- chat
- embeddings
- protocol checks
- non-stream tool calling
- streaming tool calling

## VM Direct Validation

Use this when GKE pod-to-Vertex auth is blocked but an ops VM can still call Vertex AI.

Run the container:

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

Then verify:

```bash
export PROXY_BASE_URL=http://127.0.0.1:8080
export INTERNAL_BEARER_TOKEN=replace-with-a-random-token
python3 scripts/smoke_vm_direct.py
```

This path checks:
- basic chat
- non-stream tool calling
- streaming tool calling
- embeddings

Keep production traffic on GKE after perimeter and STS policy issues are resolved. VM direct is a proof path, not the final target topology.

## In-Cluster Validation

Use this path only when GKE Workload Identity and perimeter policy are expected to be healthy.

```bash
export IN_CLUSTER_PROXY_BASE_URL=http://your-service-name:8080
export INTERNAL_BEARER_TOKEN=replace-with-a-random-token
python3 scripts/smoke_in_cluster.py
```

This covers the same basic chat, embeddings, and tool calling checks as the VM direct path, but through the in-cluster service URL.

## GKE / Workload Identity Notes

This service is meant to run on GKE with a Kubernetes service account mapped to a Google service account that can call Vertex AI.

At minimum, the mapped Google service account needs Vertex prediction permissions for the target models.

If in-cluster calls fail with errors such as:
- `organization's policy`
- `vpcServiceControlsUniqueIdentifier`

then treat that as an environment blocker first, not necessarily an application regression.
