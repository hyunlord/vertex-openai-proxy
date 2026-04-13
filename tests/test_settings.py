from importlib import reload

import pytest

import app.config as config_module


def _reload_settings(monkeypatch, **env: str) -> config_module.Settings:
    monkeypatch.setenv("INTERNAL_BEARER_TOKEN", "test-proxy-token")
    monkeypatch.delenv("VERTEX_CHAT_MODEL", raising=False)
    monkeypatch.delenv("VERTEX_CHAT_MODELS", raising=False)
    monkeypatch.delenv("VERTEX_CHAT_MODEL_ALIASES", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reloaded = reload(config_module)
    return reloaded.Settings()


def test_runtime_policy_settings_exist_with_conservative_defaults(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_BEARER_TOKEN", "test-proxy-token")
    monkeypatch.delenv("EMBEDDING_MAX_CONCURRENCY", raising=False)
    monkeypatch.delenv("EMBEDDING_MAX_INPUTS_PER_REQUEST", raising=False)
    monkeypatch.delenv("EMBEDDING_RETRY_ATTEMPTS", raising=False)
    monkeypatch.delenv("EMBEDDING_RETRY_BACKOFF_MS", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_CONCURRENCY", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_MAX_CONCURRENCY", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_WINDOW_SIZE", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_COOLDOWN_SECONDS", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_MIN_SAMPLES", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_LATENCY_UP_THRESHOLD_MS", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_LATENCY_DOWN_THRESHOLD_MS", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_FAILURE_RATE_UP_THRESHOLD", raising=False)
    monkeypatch.delenv("EMBEDDING_ADAPTIVE_FAILURE_RATE_DOWN_THRESHOLD", raising=False)
    monkeypatch.delenv("READINESS_FAIL_ON_DEGRADED", raising=False)
    monkeypatch.delenv("RUNTIME_SOFT_IN_FLIGHT_CHAT", raising=False)
    monkeypatch.delenv("RUNTIME_HARD_IN_FLIGHT_CHAT", raising=False)
    monkeypatch.delenv("RUNTIME_SOFT_IN_FLIGHT_EMBEDDINGS", raising=False)
    monkeypatch.delenv("RUNTIME_HARD_IN_FLIGHT_EMBEDDINGS", raising=False)
    monkeypatch.delenv("CHAT_MAX_IN_FLIGHT_REQUESTS", raising=False)
    monkeypatch.delenv("EMBEDDINGS_MAX_IN_FLIGHT_REQUESTS", raising=False)
    monkeypatch.delenv("RUNTIME_DEGRADED_CHAT_MAX_IN_FLIGHT", raising=False)
    monkeypatch.delenv("RUNTIME_DEGRADED_EMBEDDINGS_MAX_IN_FLIGHT", raising=False)
    monkeypatch.delenv("RUNTIME_DEGRADED_MAX_EMBEDDING_INPUTS", raising=False)
    monkeypatch.delenv("RUNTIME_HARD_CPU_PERCENT", raising=False)
    monkeypatch.delenv("RUNTIME_HARD_RSS_MB", raising=False)
    monkeypatch.delenv("QUEUE_ENABLED", raising=False)
    monkeypatch.delenv("QUEUE_DISABLE_ON_DEGRADED", raising=False)
    monkeypatch.delenv("QUEUE_POLL_INTERVAL_MS", raising=False)
    monkeypatch.delenv("QUEUE_RETRY_AFTER_SECONDS", raising=False)
    monkeypatch.delenv("CHAT_QUEUE_MAX_WAIT_MS", raising=False)
    monkeypatch.delenv("CHAT_QUEUE_MAX_DEPTH", raising=False)
    monkeypatch.delenv("EMBEDDINGS_QUEUE_MAX_WAIT_MS", raising=False)
    monkeypatch.delenv("EMBEDDINGS_QUEUE_MAX_DEPTH", raising=False)
    monkeypatch.delenv("CHAT_RETRY_ATTEMPTS", raising=False)
    monkeypatch.delenv("CHAT_RETRY_BACKOFF_MS", raising=False)

    reloaded = reload(config_module)
    settings = reloaded.Settings()

    assert settings.embedding_max_concurrency == 4
    assert settings.embedding_max_inputs_per_request == 64
    assert settings.embedding_retry_attempts == 1
    assert settings.embedding_retry_backoff_ms == 200
    assert settings.embedding_adaptive_concurrency is False
    assert settings.embedding_adaptive_max_concurrency == 16
    assert settings.embedding_adaptive_window_size == 20
    assert settings.embedding_adaptive_window_seconds == 60
    assert settings.embedding_adaptive_cooldown_seconds == 30
    assert settings.embedding_adaptive_min_samples == 5
    assert settings.embedding_adaptive_latency_up_threshold_ms == 4000.0
    assert settings.embedding_adaptive_latency_down_threshold_ms == 8000.0
    assert settings.embedding_adaptive_failure_rate_up_threshold == 0.01
    assert settings.embedding_adaptive_failure_rate_down_threshold == 0.10
    assert settings.readiness_fail_on_degraded is False
    assert settings.runtime_soft_in_flight_chat == 50
    assert settings.runtime_hard_in_flight_chat == 100
    assert settings.runtime_soft_in_flight_embeddings == 10
    assert settings.runtime_hard_in_flight_embeddings == 20
    assert settings.chat_max_in_flight_requests == 200
    assert settings.embeddings_max_in_flight_requests == 40
    assert settings.runtime_degraded_chat_max_in_flight == 20
    assert settings.runtime_degraded_embeddings_max_in_flight == 4
    assert settings.runtime_degraded_max_embedding_inputs == 16
    assert settings.runtime_hard_cpu_percent == 90.0
    assert settings.runtime_hard_rss_mb == 1024.0
    assert settings.queue_enabled is False
    assert settings.queue_disable_on_degraded is True
    assert settings.queue_poll_interval_ms == 25
    assert settings.queue_retry_after_seconds == 1
    assert settings.chat_queue_max_wait_ms == 200
    assert settings.chat_queue_max_depth == 8
    assert settings.embeddings_queue_max_wait_ms == 1000
    assert settings.embeddings_queue_max_depth == 4
    assert settings.chat_retry_attempts == 1
    assert settings.chat_retry_backoff_ms == 200


@pytest.mark.parametrize(
    "token",
    ["", "change-me", "replace-with-a-random-token"],
)
def test_validate_runtime_settings_rejects_insecure_bearer_tokens(monkeypatch, token: str) -> None:
    monkeypatch.setattr(config_module.settings, "internal_bearer_token", token)

    with pytest.raises(RuntimeError):
        config_module.validate_runtime_settings()


def test_validate_runtime_settings_accepts_non_default_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "internal_bearer_token", "test-proxy-token")

    config_module.validate_runtime_settings()


def test_chat_model_settings_include_default_and_additional_models(monkeypatch) -> None:
    settings = _reload_settings(
        monkeypatch,
        VERTEX_CHAT_MODEL="google/gemini-3.1-flash-lite-preview",
        VERTEX_CHAT_MODELS="google/gemini-3.1-pro-preview,google/gemini-3.1-flash-lite-preview",
    )

    assert settings.allowed_chat_models() == (
        "google/gemini-3.1-flash-lite-preview",
        "google/gemini-3.1-pro-preview",
    )


def test_chat_model_aliases_are_parsed_into_mapping(monkeypatch) -> None:
    settings = _reload_settings(
        monkeypatch,
        VERTEX_CHAT_MODEL="google/gemini-3.1-flash-lite-preview",
        VERTEX_CHAT_MODELS="google/gemini-3.1-pro-preview",
        VERTEX_CHAT_MODEL_ALIASES=(
            "genos-flash=google/gemini-3.1-flash-lite-preview,"
            "genos-pro=google/gemini-3.1-pro-preview"
        ),
    )

    assert settings.chat_model_alias_map() == {
        "genos-flash": "google/gemini-3.1-flash-lite-preview",
        "genos-pro": "google/gemini-3.1-pro-preview",
    }


def test_invalid_chat_model_alias_target_is_rejected(monkeypatch) -> None:
    settings = _reload_settings(
        monkeypatch,
        VERTEX_CHAT_MODEL="google/gemini-3.1-flash-lite-preview",
        VERTEX_CHAT_MODEL_ALIASES="genos-pro=google/gemini-3.1-pro-preview",
    )

    with pytest.raises(RuntimeError, match="must reference a configured chat model"):
        settings.chat_model_alias_map()


def test_invalid_chat_model_alias_syntax_is_rejected(monkeypatch) -> None:
    settings = _reload_settings(
        monkeypatch,
        VERTEX_CHAT_MODEL="google/gemini-3.1-flash-lite-preview",
        VERTEX_CHAT_MODEL_ALIASES="genos-pro",
    )

    with pytest.raises(RuntimeError, match="must use alias=model format"):
        settings.chat_model_alias_map()
