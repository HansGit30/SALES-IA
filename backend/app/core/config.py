from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SalesIA Enterprise API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://salesia:salesia@localhost:5432/salesia"
    database_connect_timeout: int = Field(default=15,ge=1,le=60)
    database_pool_timeout: int = Field(default=15,ge=1,le=60)
    database_pool_recycle: int = Field(default=300,ge=30,le=3600)
    secret_key: str = "replace-this-development-secret-before-deploying-00000000"
    access_token_minutes: int = Field(default=60, ge=1, le=1440)
    auth_window_seconds: int = Field(default=900, ge=60, le=86400)
    auth_account_attempts: int = Field(default=10, ge=1, le=1000)
    auth_ip_attempts: int = Field(default=100, ge=1, le=10000)
    cors_origins: str = "http://localhost:5173"

    @model_validator(mode="after")
    def reject_weak_production_secret(self):
        if self.environment.lower() in {"prod", "production"} and (len(self.secret_key) < 32 or self.secret_key.lower().startswith("replace-")):
            raise ValueError("SECRET_KEY debe ser un secreto aleatorio de al menos 32 caracteres en producción")
        return self
    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()


