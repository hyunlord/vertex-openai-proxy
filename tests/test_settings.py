from importlib import reload

import app.config as config_module


def test_runtime_policy_settings_exist_with_conservative_defaults(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_MAX_CONCURRENCY", raising=False)
    monkeypatch.delenv("EMBEDDING_MAX_INPUTS_PER_REQUEST", raising=False)
    monkeypatch.delenv("EMBEDDING_RETRY_ATTEMPTS", raising=False)
    monkeypatch.delenv("EMBEDDING_RETRY_BACKOFF_MS", raising=False)
    monkeypatch.delenv("CHAT_RETRY_ATTEMPTS", raising=False)
    monkeypatch.delenv("CHAT_RETRY_BACKOFF_MS", raising=False)

    reloaded = reload(config_module)
    settings = reloaded.Settings()

    assert settings.embedding_max_concurrency == 4
    assert settings.embedding_max_inputs_per_request == 64
    assert settings.embedding_retry_attempts == 1
    assert settings.embedding_retry_backoff_ms == 200
    assert settings.chat_retry_attempts == 1
    assert settings.chat_retry_backoff_ms == 200
