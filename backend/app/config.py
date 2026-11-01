from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_secret_key: str = "changeme"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://algomentor:algomentor@localhost:5432/algomentor"
    database_url_sync: str = "postgresql://algomentor:algomentor@localhost:5432/algomentor"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Judge0
    judge0_url: str = "http://localhost:2358"
    judge0_auth_token: str = ""

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cheap_llm_provider: str = "openai"
    cheap_llm_model: str = "gpt-4o-mini"
    frontier_llm_provider: str = "openai"
    frontier_llm_model: str = "gpt-4o"

    # Auth
    clerk_secret_key: str = ""
    clerk_jwks_url: str = "https://api.clerk.dev/v1/jwks"
    jwt_secret_key: str = "dev-local-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
