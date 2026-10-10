"""Server configuration using Pydantic Settings."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """Immutable application settings validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    port: int = Field(default=8080, alias="SERVER_PORT")
    environment: str = Field(default="development", alias="SERVER_ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    timezone: str = Field(default="America/Sao_Paulo", alias="TZ")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/beatstar.db",
        alias="DATABASE_URL",
    )

    public_host: str = Field(
        default="beatstar.dev.timoteo.mg.gov.br",
        alias="GATEWAY_PUBLIC_HOST",
    )
    public_port: int = Field(default=8080, alias="GATEWAY_PUBLIC_PORT")
    use_ssl: bool = Field(default=False, alias="GATEWAY_USE_SSL")
    assets_base_url: str = Field(
        default="http://beatstar.dev.timoteo.mg.gov.br:8080/assets",
        alias="ASSETS_BASE_URL",
    )

    asset_storage_root: Path = Field(default=Path("data"), alias="ASSET_STORAGE_ROOT")
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    # Administration (separate from game tickets; admin routes stay unmounted without a secret)
    admin_auth_secret: SecretStr | None = Field(default=None, alias="ADMIN_AUTH_SECRET")
    admin_session_lifetime_seconds: int = Field(default=8 * 60 * 60, alias="ADMIN_SESSION_LIFETIME_SECONDS")
    admin_cookie_secure: bool = Field(default=True, alias="ADMIN_COOKIE_SECURE")
    admin_login_max_attempts: int = Field(default=5, alias="ADMIN_LOGIN_MAX_ATTEMPTS")
    admin_login_window_seconds: int = Field(default=900, alias="ADMIN_LOGIN_WINDOW_SECONDS")

    jwt_secret_key: str = Field(
        default="beatstar-default-secret-key-32chars-minimum!",
        alias="JWT_SECRET_KEY",
    )
    session_expiration_hours: int = Field(
        default=24,
        alias="SESSION_EXPIRATION_HOURS",
    )

    # Feature Flags & Monetização (Google Ads / AdMob)
    feature_flag_google_ads_enabled: bool = Field(
        default=False,
        alias="FEATURE_FLAG_GOOGLE_ADS_ENABLED",
    )
    google_ads_app_id: str = Field(
        default="ca-app-pub-3940256099942544~3347511713",
        alias="GOOGLE_ADS_APP_ID",
    )
    google_ads_rewarded_unit_id: str = Field(
        default="ca-app-pub-3940256099942544/5224354917",
        alias="GOOGLE_ADS_REWARDED_UNIT_ID",
    )
    google_ads_interstitial_unit_id: str = Field(
        default="ca-app-pub-3940256099942544/1033173712",
        alias="GOOGLE_ADS_INTERSTITIAL_UNIT_ID",
    )

    # Feature Flags de Compras, Economia e Loja (In-App Purchases & SDK)
    feature_flag_iap_enabled: bool = Field(
        default=False,
        alias="FEATURE_FLAG_IAP_ENABLED",
    )
    feature_flag_shop_enabled: bool = Field(
        default=True,
        alias="FEATURE_FLAG_SHOP_ENABLED",
    )
    feature_flag_lootboxes_enabled: bool = Field(
        default=True,
        alias="FEATURE_FLAG_LOOTBOXES_ENABLED",
    )
    feature_flag_premium_pass_enabled: bool = Field(
        default=True,
        alias="FEATURE_FLAG_PREMIUM_PASS_ENABLED",
    )
    feature_flag_cosmetics_enabled: bool = Field(
        default=True,
        alias="FEATURE_FLAG_COSMETICS_ENABLED",
    )
    feature_flag_player_ticket_enforcement_enabled: bool = Field(
        default=False,
        alias="FEATURE_FLAG_PLAYER_TICKET_ENFORCEMENT_ENABLED",
    )



settings = ServerSettings()
