"""In-process failed-login limiter; valid for the single-worker deployment only."""

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException


class LoginAttemptLimiter:
    """Counts failed logins per client address inside a sliding window."""

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Stores the limits; clock is injectable for deterministic tests."""
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def ensure_allowed(self, client: str) -> None:
        """Raises 429 when the client has reached the failure limit inside the window.

        Raises:
            HTTPException: status 429 with a Retry-After header.
        """
        failures = self._recent_failures(client)
        if len(failures) < self._max_attempts:
            return
        retry_after = int(failures[0] + self._window_seconds - self._clock()) + 1
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    def record_failure(self, client: str) -> None:
        """Records one failed login attempt for the client."""
        self._recent_failures(client).append(self._clock())

    def reset(self, client: str) -> None:
        """Clears failures after a successful login."""
        self._failures.pop(client, None)

    def _recent_failures(self, client: str) -> deque[float]:
        """Drops expired timestamps and returns the remaining failures for the client."""
        failures = self._failures[client]
        cutoff = self._clock() - self._window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures
