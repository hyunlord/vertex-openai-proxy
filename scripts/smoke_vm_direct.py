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


def _build_tool_payload(chat_model: str) -> dict:
    return {
        "model": chat_model,
        "messages": [{"role": "user", "content": "What is the weather in Seoul?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather",
                },
            }
        ],
        "tool_choice": "auto",
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
        tool_chat = _call(
            base_url,
            token,
            "/v1/chat/completions",
            _build_tool_payload(chat_model),
        )
        tool_stream = _call(
            base_url,
            token,
            "/v1/chat/completions",
            {**_build_tool_payload(chat_model), "stream": True},
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
        chat_body = json.loads(chat["body"])
        tool_chat_body = json.loads(tool_chat["body"])
        embeddings_body = json.loads(embeddings["body"])
        chat_text = chat_body["choices"][0]["message"]["content"]
        embedding_count = len(embeddings_body["data"])

        results = {
            "ok": (
                health["status"] == 200
                and models["status"] == 200
                and chat["status"] == 200
                and tool_chat["status"] == 200
                and tool_stream["status"] == 200
                and embeddings["status"] == 200
                and tool_chat_body["choices"][0]["message"]["tool_calls"][0]["id"] == "call_weather"
                and '"tool_calls"' in tool_stream["body"]
                and "data: [DONE]" in tool_stream["body"]
                and embedding_count == 3
            ),
            "health_status": health["status"],
            "models_status": models["status"],
            "chat_status": chat["status"],
            "tool_chat_status": tool_chat["status"],
            "tool_stream_status": tool_stream["status"],
            "embeddings_status": embeddings["status"],
            "chat_model": chat_model,
            "embedding_model": embedding_model,
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
