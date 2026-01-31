from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_name: str = "fridge-recipes"
    cors_origins: str = "http://localhost:3000"

    # Optional
    database_url: str | None = None

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"

    # Coupang
    coupang_partners_tracking_id: str | None = None
    coupang_partners_sub_id: str | None = None


settings = Settings()
