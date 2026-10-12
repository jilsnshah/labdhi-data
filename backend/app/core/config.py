"""Application configuration, loaded from environment / .env."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Trader CRM"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://trader:trader@localhost:5433/trader_crm"
    test_database_url: str = "postgresql+psycopg://trader:trader@localhost:5433/trader_crm_test"
    sql_echo: bool = False

    #: Business day boundaries ("today", "upcoming") are evaluated in this
    #: offset from UTC. Default +05:30 (IST) - the trader's local day.
    display_timezone_offset_minutes: int = 330

    #: Activity types a salesperson may schedule as a follow-up from the field app.
    salesperson_followup_types: str = "CALL,WHATSAPP,SMS,VISIT"
    #: Minutes around a scheduled activity used to warn about double booking.
    schedule_conflict_window_minutes: int = 60

    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    seed_admin_email: str = "admin@tradercrm.in"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "Trade Desk Admin"

    #: Comma separated list; parsed by :attr:`cors_origin_list`.
    #: 5173 = admin web app, 5174 = field web app; the localhost schemes are the
    #: origins used by the Capacitor WebView inside the APK.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "https://localhost,capacitor://localhost"
    )

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _psycopg_driver(cls, value: str) -> str:
        """Hosted Postgres (Render, Neon) hands out ``postgres://`` / ``postgresql://``
        URLs; SQLAlchemy needs the driver named to use psycopg 3."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def _production_secrets(self) -> "Settings":
        if self.is_production and self.secret_key in {"", "change-me"}:
            raise ValueError("SECRET_KEY must be set to a random value in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


#: Activity types a salesperson may schedule as a follow-up from the mobile app.
#: Configurable via SALESPERSON_FOLLOWUP_TYPES (comma separated).
def salesperson_followup_types() -> list[str]:
    raw = settings.salesperson_followup_types
    return [item.strip().upper() for item in raw.split(",") if item.strip()]
