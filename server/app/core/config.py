"""Configuration settings for the FastAPI application."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with Pydantic validation."""

    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/dbname",
        env="DATABASE_URL",
        description="PostgreSQL async database URL"
    )

    # Environment settings
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Application environment"
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Application log level"
    )

    # Security settings
    bearer_token_secret: str = Field(
        default="your-secret-key-here",
        env="BEARER_TOKEN_SECRET",
        description="Secret key for bearer token validation"
    )

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3001", "http://localhost:8001", "http://localhost:3000"],
        description="Allowed CORS origins"
    )

    # Server settings
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host"
    )

    port: int = Field(
        default=8000,
        env="PORT",
        description="Server port"
    )

    # Idempotency settings
    idempotency_ttl_seconds: int = Field(
        default=3600,
        env="IDEMPOTENCY_TTL_SECONDS",
        description="Time-to-live for idempotency keys in seconds"
    )

    idempotency_cache_size: int = Field(
        default=10000,
        env="IDEMPOTENCY_CACHE_SIZE",
        description="Maximum number of idempotency keys to cache"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_environments = ["development", "staging", "production"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def debug(self) -> bool:
        """Return True if in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Return True if in production mode."""
        return self.environment == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()
