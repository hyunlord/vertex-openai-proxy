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
    chat_retry_attempts: int = 1
    chat_retry_backoff_ms: int = 200
    vertex_access_token: str | None = None


settings = Settings()
