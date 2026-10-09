"""Administrator authentication settings, validated before any route is mounted."""

from dataclasses import dataclass, field

MINIMUM_SECRET_LENGTH = 32
DEFAULT_SESSION_LIFETIME_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class AdminAuthSettings:
    """Immutable administrator authentication configuration.

    Attributes:
        secret: Signing secret for reset and verification tokens; never the game JWT secret.
        session_lifetime_seconds: Maximum age of a database-backed session.
        cookie_secure: Marks the session cookie HTTPS-only; disable only for local development.
        allowed_origins: Exact origins permitted to send unsafe admin requests.
        login_max_attempts: Failed logins allowed per client within the window.
        login_window_seconds: Length of the failed-login window.
    """

    secret: str
    session_lifetime_seconds: int = DEFAULT_SESSION_LIFETIME_SECONDS
    cookie_secure: bool = True
    allowed_origins: tuple[str, ...] = field(default_factory=tuple)
    login_max_attempts: int = 5
    login_window_seconds: int = 900

    def __post_init__(self) -> None:
        """Rejects weak secrets and non-positive limits before the application starts.

        Raises:
            ValueError: when the secret is too short or a limit is not positive.
        """
        if len(self.secret) < MINIMUM_SECRET_LENGTH:
            raise ValueError(f"Admin secret must be at least {MINIMUM_SECRET_LENGTH} characters")
        for name in ("session_lifetime_seconds", "login_max_attempts", "login_window_seconds"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
