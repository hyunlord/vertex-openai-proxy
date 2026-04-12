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
