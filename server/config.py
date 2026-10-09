"""Server configuration using Pydantic Settings."""

from __future__ import annotations

import os
from pydantic import Field
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


settings = ServerSettings()
