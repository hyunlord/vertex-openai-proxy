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
    vertex_access_token: str | None = None


settings = Settings()
