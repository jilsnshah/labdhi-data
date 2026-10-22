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

    #: Where the bidding portal lives, as a participant reaches it.
    #:
    #: Links in a WhatsApp invitation are opened on someone else's phone, so
    #: they cannot be built from whatever host the desk happens to be using:
    #: an admin working on localhost would otherwise send dead links. Set this
    #: to the public web address and every link is built from it. Left empty,
    #: the request's own origin is used, which is right for local work.
    portal_base_url: str = ""
    #: Requests a single caller may make to the public bidding portal each
    #: minute. A bidder watching one auction polls a handful of times; this is
    #: set well above that and only bites on someone probing for codes.
    portal_rate_limit_per_minute: int = 240

    # --- WhatsApp (Meta Cloud API) ---
    #: Permanent or test access token from the Meta app. Empty means "not
    #: configured", and the service then reports every send skipped rather
    #: than failing a bid.
    whatsapp_access_token: str = ""
    #: The sending number's id in the Meta app, not the number itself.
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"
    #: Invitations go as plain text.
    #:
    #: Verified against a real handset, in both directions: WhatsApp delivers
    #: free text to someone who has written to the business number in the last
    #: 24 hours, and silently drops it for anyone who has not - accepting the
    #: call, returning a message id, and reporting no error. Nothing in the
    #: response distinguishes the two, so a party must message the desk once
    #: before invitations can reach them. Set this true to send the approved
    #: template instead, which has no such window.
    whatsapp_use_template: bool = False
    #: Shared with Meta when the webhook URL is first saved, and echoed back
    #: on their subscribe handshake. Any string; it only has to match.
    whatsapp_verify_token: str = ""
    #: The Meta app secret, used to check that a webhook really came from them.
    #: Without it nothing inbound is accepted in production, because an open
    #: endpoint that writes to the database is worse than one that is not
    #: working yet.
    whatsapp_app_secret: str = ""
    #: The template Meta approved, used when this is switched on.
    whatsapp_bid_template: str = "bid_invitation"
    #: Language of the approved template, as registered with Meta.
    whatsapp_language: str = "en"
    #: Assumed when a number is written as ten bare digits.
    whatsapp_default_country_code: str = "91"
    whatsapp_timeout_seconds: float = 15.0

    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    #: 30 days. A trader opening the app each morning, and a salesperson whose
    #: phone sits in a pocket all week, should not be asked to sign in again;
    #: the clients renew the token on every launch, so a session only lapses
    #: after a month of not being used at all.
    access_token_expire_minutes: int = 60 * 24 * 30

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
