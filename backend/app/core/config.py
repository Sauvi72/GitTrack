from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator, model_validator
import json


class Settings(BaseSettings):
    APP_NAME: str = "OpenTrack"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "opentrack-development-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = "sqlite:///./opentrack.db"
    
    # GitHub Integration
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_MAX_RETRIES: int = 3
    GITHUB_RETRY_BACKOFF: float = 1.5
    
    # Initial Teacher Seed
    INITIAL_TEACHER_EMAIL: str = "teacher@opentrack.edu"
    INITIAL_TEACHER_PASSWORD: str = "OpenTrack2026!"
    INITIAL_TEACHER_NAME: str = "Prof. Davis"
    
    # Timezone
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Automated Background Synchronization
    AUTO_SYNC_ENABLED: bool = True
    AUTO_SYNC_INTERVAL_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV.lower() == "production":
            if "change-in-production" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "In production, SECRET_KEY must be a cryptographically secure random string with at least 32 characters."
                )
            if self.INITIAL_TEACHER_PASSWORD == "OpenTrack2026!":
                raise ValueError(
                    "In production, INITIAL_TEACHER_PASSWORD must be changed from the development default."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
