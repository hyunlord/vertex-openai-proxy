from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "vertex-openai-proxy"
    internal_bearer_token: str = "change-me"
    vertex_project_id: str = "your-gcp-project-id"
    vertex_chat_location: str = "global"
    vertex_embedding_location: str = "us-central1"
    vertex_chat_model: str = "google/gemini-2.5-flash"
    vertex_embedding_model: str = "gemini-embedding-2-preview"
    request_timeout_seconds: float = 60.0
    embedding_max_concurrency: int = 4
    embedding_max_inputs_per_request: int = 64
    embedding_retry_attempts: int = 1
    embedding_retry_backoff_ms: int = 200
    embedding_adaptive_concurrency: bool = False
    embedding_adaptive_max_concurrency: int = 16
    embedding_adaptive_window_size: int = 20
    embedding_adaptive_window_seconds: int = 60
    embedding_adaptive_cooldown_seconds: int = 30
    embedding_adaptive_min_samples: int = 5
    embedding_adaptive_latency_up_threshold_ms: float = 4000.0
    embedding_adaptive_latency_down_threshold_ms: float = 8000.0
    embedding_adaptive_failure_rate_up_threshold: float = 0.01
    embedding_adaptive_failure_rate_down_threshold: float = 0.10
    runtime_adaptive_mode: bool = False
    readiness_fail_on_degraded: bool = False
    runtime_window_size: int = 50
    runtime_window_seconds: int = 60
    runtime_recovery_seconds: int = 30
    runtime_soft_in_flight_chat: int = 50
    runtime_hard_in_flight_chat: int = 100
    runtime_soft_in_flight_embeddings: int = 10
    runtime_hard_in_flight_embeddings: int = 20
    chat_max_in_flight_requests: int = 200
    embeddings_max_in_flight_requests: int = 40
    runtime_degraded_chat_max_in_flight: int = 20
    runtime_degraded_embeddings_max_in_flight: int = 4
    runtime_degraded_max_embedding_inputs: int = 16
    runtime_chat_soft_latency_ms: float = 6000.0
    runtime_chat_hard_latency_ms: float = 12000.0
    runtime_embeddings_soft_latency_ms: float = 4000.0
    runtime_embeddings_hard_latency_ms: float = 8000.0
    runtime_soft_retryable_error_rate: float = 0.02
    runtime_hard_retryable_error_rate: float = 0.10
    runtime_soft_timeout_rate: float = 0.01
    runtime_hard_timeout_rate: float = 0.05
    runtime_hard_cpu_percent: float = 90.0
    runtime_hard_rss_mb: float = 1024.0
    queue_enabled: bool = False
    queue_disable_on_degraded: bool = True
    queue_poll_interval_ms: int = 25
    queue_retry_after_seconds: int = 1
    chat_queue_max_wait_ms: int = 200
    chat_queue_max_depth: int = 8
    embeddings_queue_max_wait_ms: int = 1000
    embeddings_queue_max_depth: int = 4
    chat_retry_attempts: int = 1
    chat_retry_backoff_ms: int = 200
    vertex_access_token: str | None = None


settings = Settings()
