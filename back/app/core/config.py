from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_name: str = "fridge-recipes"
    cors_origins: str = "http://localhost:3000"

    # Database (PostgreSQL via Supabase)
    database_url: str | None = None

    # JWT Authentication
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    # Recipe Provider (youtube | anthropic | mock)
    recipe_provider: str = "youtube"

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-5-20250929"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4000

    # YouTube Data API v3
    youtube_api_key: str | None = None

    # Haiku (YouTube 영상 구조화용)
    haiku_model: str = "claude-haiku-4-5-20251001"
    haiku_max_tokens: int = 3000
    haiku_temperature: float = 0.3

    # Kakao OAuth
    kakao_rest_api_key: str | None = None
    kakao_client_secret: str | None = None

    # Coupang
    coupang_partners_tracking_id: str | None = None
    coupang_partners_sub_id: str | None = None

    # Image Search
    image_search_provider: str = "google"  # google | unsplash | gemini | mock
    google_api_key: str | None = None
    google_search_engine_id: str | None = None
    image_search_timeout: int = 3
    image_cache_enabled: bool = True

    # Usage limits
    guest_daily_limit: int = 3
    user_daily_limit: int = 30  # 로그인 사용자 일일 제한

    # Sentry
    sentry_dsn: str = ""

    # Claude Code CLI (headless mode)
    claude_binary: str = "claude"
    claude_subprocess_timeout: int = 120

    # Concurrency & Cache
    max_concurrent_llm: int = 3  # 동시 LLM subprocess 최대 수 (워커별)
    cache_expiry_days: int = 14  # 캐시 만료일

    # Gemini (이미지 생성용) - 유료 계정 필요
    gemini_api_key: str | None = None
    # 옵션: gemini-2.0-flash-exp-image-generation (기본), imagen-4.0-generate-001 (유료 전용)
    gemini_image_model: str = "gemini-2.0-flash-exp-image-generation"
    # 정밀 모드 전용 이미지 모델 (이미지 생성 지원 모델만 사용)
    gemini_detailed_image_model: str = "gemini-2.0-flash-exp-image-generation"


settings = Settings()
