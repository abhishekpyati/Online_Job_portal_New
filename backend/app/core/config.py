from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://job_user:job_password@localhost:3306/job_portal"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8090,http://127.0.0.1:8090"
    UPLOAD_DIR: str = "../uploads"
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@12345"
    # OpenAI API key must be set in the backend/.env file, not hardcoded in source.
    OPENAI_API_KEY: str | None = None
    AI_MODEL: str = "gpt-3.5-turbo"

    model_config = SettingsConfigDict(env_file=str(Path(__file__).parent.parent.parent / ".env"), case_sensitive=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
