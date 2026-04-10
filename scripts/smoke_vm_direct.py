from __future__ import annotations

import json
import os
import sys
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


def main() -> None:
    if os.getenv("HARNESS_SELFTEST") == "1":
        print(json.dumps({"ok": True, "mode": "vm_direct_selftest"}))
        return

    try:
        base_url = os.environ["PROXY_BASE_URL"].rstrip("/")
        token = os.environ["INTERNAL_BEARER_TOKEN"]
    except KeyError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"missing environment variable: {exc.args[0]}",
                    "required": ["PROXY_BASE_URL", "INTERNAL_BEARER_TOKEN"],
                }
            )
        )
        raise SystemExit(1) from exc

    results: dict[str, object] = {"ok": False}
    try:
        health = _call(base_url, token, "/health")
        models = _call(base_url, token, "/v1/models")
        chat = _call(
            base_url,
            token,
            "/v1/chat/completions",
            {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": "reply with READY only"}],
            },
        )
        embeddings = _call(
            base_url,
            token,
            "/v1/embeddings",
            {
                "model": "gemini-embedding-2-preview",
                "input": ["alpha", "beta", "gamma"],
            },
        )
        chat_body = json.loads(chat["body"])
        embeddings_body = json.loads(embeddings["body"])
        chat_text = chat_body["choices"][0]["message"]["content"]
        embedding_count = len(embeddings_body["data"])

        results = {
            "ok": (
                health["status"] == 200
                and models["status"] == 200
                and chat["status"] == 200
                and embeddings["status"] == 200
                and embedding_count == 3
            ),
            "health_status": health["status"],
            "models_status": models["status"],
            "chat_status": chat["status"],
            "embeddings_status": embeddings["status"],
            "chat_preview": chat_text[:120],
            "embedding_count": embedding_count,
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
