from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.checks.protocol import (
    validate_chat_chunk,
    validate_chat_completion,
    validate_embeddings_response,
    validate_openai_error,
)


def main() -> None:
    sample_chat = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1710000000,
        "model": "google/gemini-2.5-flash",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }
    sample_chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1710000000,
        "model": "google/gemini-2.5-flash",
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"}}],
    }
    sample_embeddings = {
        "object": "list",
        "data": [
            {"object": "embedding", "index": 0, "embedding": [0.1]},
            {"object": "embedding", "index": 1, "embedding": [0.2]},
        ],
    }
    sample_error = {
        "error": {
            "message": "bad request",
            "type": "invalid_request_error",
            "code": 400,
        }
    }

    print(
        json.dumps(
            {
                "ok": all(
                    [
                        validate_chat_completion(sample_chat),
                        validate_chat_chunk(sample_chunk),
                        validate_embeddings_response(sample_embeddings, expected_count=2),
                        validate_openai_error(sample_error),
                    ]
                )
            }
        )
    )


if __name__ == "__main__":
    main()
