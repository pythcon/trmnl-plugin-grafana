"""Configuration management for the data service."""

from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class Config:
    """Data service configuration loaded from environment variables."""

    # Grafana connection
    grafana_url: str
    grafana_api_key: str

    # Panel configuration
    dashboard_uid: str
    panel_id: int
    time_from: str
    time_to: str

    # TRMNL webhook
    trmnl_webhook_url: str

    # Optional settings
    interval: int  # Seconds between updates
    label: str  # Prometheus label key for display names


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Required:
        - GRAFANA_URL: Base URL of Grafana instance
        - GRAFANA_API_KEY: Grafana API key/service account token
        - DASHBOARD_UID: UID of the dashboard containing the panel
        - PANEL_ID: ID of the panel to display
        - TRMNL_WEBHOOK_URL: TRMNL plugin webhook URL

    Optional:
        - TIME_FROM: Start of time range (default: now-1h)
        - TIME_TO: End of time range (default: now)
        - INTERVAL: Seconds between updates (default: 300)

    Raises:
        ConfigError: If required environment variables are missing.
    """
    load_dotenv()

    errors: list[str] = []

    # Required fields
    grafana_url = environ.get("GRAFANA_URL", "").rstrip("/")
    if not grafana_url:
        errors.append("GRAFANA_URL is required")

    grafana_api_key = environ.get("GRAFANA_API_KEY", "")
    if not grafana_api_key:
        errors.append("GRAFANA_API_KEY is required")

    dashboard_uid = environ.get("DASHBOARD_UID", "")
    if not dashboard_uid:
        errors.append("DASHBOARD_UID is required")

    panel_id_str = environ.get("PANEL_ID", "")
    if not panel_id_str:
        errors.append("PANEL_ID is required")

    trmnl_webhook_url = environ.get("TRMNL_WEBHOOK_URL", "")
    if not trmnl_webhook_url:
        errors.append("TRMNL_WEBHOOK_URL is required")

    if errors:
        raise ConfigError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    # Parse panel ID
    try:
        panel_id = int(panel_id_str)
    except ValueError:
        raise ConfigError(f"PANEL_ID must be an integer, got: {panel_id_str}")

    # Parse interval
    interval_str = environ.get("INTERVAL", "300")
    try:
        interval = int(interval_str)
    except ValueError:
        interval = 300

    return Config(
        grafana_url=grafana_url,
        grafana_api_key=grafana_api_key,
        dashboard_uid=dashboard_uid,
        panel_id=panel_id,
        time_from=environ.get("TIME_FROM", "now-1h"),
        time_to=environ.get("TIME_TO", "now"),
        trmnl_webhook_url=trmnl_webhook_url,
        interval=interval,
        label=environ.get("LABEL", "name"),
    )
