from importlib import reload

import app.config as config_module


def test_runtime_policy_settings_exist_with_conservative_defaults(monkeypatch) -> None:
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
    assert settings.chat_retry_attempts == 1
    assert settings.chat_retry_backoff_ms == 200
