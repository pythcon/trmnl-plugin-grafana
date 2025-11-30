"""Custom exceptions for Grafana API operations."""


class GrafanaAPIError(Exception):
    """Base exception for Grafana API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class GrafanaAuthError(GrafanaAPIError):
    """Raised when authentication fails (401/403)."""

    def __init__(self, message: str = "Invalid or expired API key"):
        super().__init__(message, status_code=401)


class GrafanaNotFoundError(GrafanaAPIError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class GrafanaConnectionError(GrafanaAPIError):
    """Raised when connection to Grafana fails."""

    def __init__(self, message: str = "Failed to connect to Grafana"):
        super().__init__(message)
