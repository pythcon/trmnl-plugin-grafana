"""Rate limiting per Grafana URL."""

import os
import time
from collections import defaultdict


class RateLimiter:
    """In-memory sliding window rate limiter per Grafana URL."""

    def __init__(self):
        # Dict of grafana_url -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._window = 60  # 1 minute window

    @property
    def limit(self) -> int | None:
        """Get rate limit from env. Returns None if disabled."""
        val = os.environ.get("RATE_LIMIT", "")
        if not val:
            return None
        try:
            return int(val)
        except ValueError:
            return None

    def is_allowed(self, grafana_url: str) -> bool:
        """Check if request is allowed for this grafana_url."""
        limit = self.limit
        if limit is None:
            return True  # Rate limiting disabled

        now = time.time()
        cutoff = now - self._window

        # Clean old requests and get current count
        self._requests[grafana_url] = [
            ts for ts in self._requests[grafana_url] if ts > cutoff
        ]

        if len(self._requests[grafana_url]) >= limit:
            return False

        self._requests[grafana_url].append(now)
        return True

    def get_retry_after(self, grafana_url: str) -> int:
        """Get seconds until next request is allowed."""
        if not self._requests[grafana_url]:
            return 0
        oldest = min(self._requests[grafana_url])
        return max(1, int(self._window - (time.time() - oldest)))


# Global instance
rate_limiter = RateLimiter()
