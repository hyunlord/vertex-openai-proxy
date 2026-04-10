from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def _call(base_url: str, token: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        base_url + path,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return {
            "status": response.status,
            "body": response.read().decode(),
        }


def _select_model(models_payload: dict, capability_kind: str, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model
    for model in models_payload.get("data", []):
        capabilities = model.get("capabilities", [])
        if any(capability.get("kind") == capability_kind for capability in capabilities):
            model_id = model.get("id")
            if isinstance(model_id, str):
                return model_id
    raise ValueError(f"no model found for capability={capability_kind}")


def main() -> None:
    if os.getenv("HARNESS_SELFTEST") == "1":
        print(json.dumps({"ok": True, "mode": "in_cluster_selftest"}))
        return

    try:
        base_url = os.environ["IN_CLUSTER_PROXY_BASE_URL"].rstrip("/")
        token = os.environ["INTERNAL_BEARER_TOKEN"]
    except KeyError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"missing environment variable: {exc.args[0]}",
                    "required": ["IN_CLUSTER_PROXY_BASE_URL", "INTERNAL_BEARER_TOKEN"],
                }
            )
        )
        raise SystemExit(1) from exc

    results: dict[str, object] = {"ok": False}
    try:
        health = _call(base_url, token, "/health")
        models = _call(base_url, token, "/v1/models")
        models_body = json.loads(models["body"])
        chat_model = _select_model(models_body, "chat", os.getenv("CHAT_MODEL"))
        embedding_model = _select_model(
            models_body,
            "embedding",
            os.getenv("EMBEDDING_MODEL"),
        )
        chat = _call(
            base_url,
            token,
            "/v1/chat/completions",
            {
                "model": chat_model,
                "messages": [{"role": "user", "content": "reply with READY only"}],
            },
        )
        embeddings = _call(
            base_url,
            token,
            "/v1/embeddings",
            {
                "model": embedding_model,
                "input": ["alpha", "beta", "gamma"],
            },
        )
        results = {
            "ok": (
                health["status"] == 200
                and models["status"] == 200
                and chat["status"] == 200
                and embeddings["status"] == 200
                and len(json.loads(embeddings["body"])["data"]) == 3
            ),
            "health_status": health["status"],
            "models_status": models["status"],
            "chat_status": chat["status"],
            "embeddings_status": embeddings["status"],
            "chat_model": chat_model,
            "embedding_model": embedding_model,
        }
    except urllib.error.HTTPError as exc:
        results = {
            "ok": False,
            "status": exc.code,
            "body": exc.read().decode()[:2000],
        }
    except Exception as exc:
        results = {"ok": False, "error": repr(exc)}

    print(json.dumps(results))
    if not results.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
