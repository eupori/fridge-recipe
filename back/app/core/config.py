from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_name: str = "fridge-recipes"
    cors_origins: str = "http://localhost:3000"

    # Optional
    database_url: str | None = None

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-5-20250929"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4000

    # Coupang
    coupang_partners_tracking_id: str | None = None
    coupang_partners_sub_id: str | None = None

    # Image Search
    image_search_provider: str = "google"  # google | unsplash | gemini | mock
    google_api_key: str | None = None
    google_search_engine_id: str | None = None
    image_search_timeout: int = 3
    image_cache_enabled: bool = True

    # Gemini (이미지 생성용) - 유료 계정 필요
    gemini_api_key: str | None = None
    # 옵션: gemini-2.0-flash-exp-image-generation (기본), imagen-4.0-generate-001 (유료 전용)
    gemini_image_model: str = "gemini-2.0-flash-exp-image-generation"


settings = Settings()
