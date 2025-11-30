"""HTTP client for Grafana API."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

from .exceptions import (
    GrafanaAPIError,
    GrafanaAuthError,
    GrafanaConnectionError,
    GrafanaNotFoundError,
)
from .models import Dashboard, Panel, QueryResult

# Grafana built-in variables with sensible defaults
# These are computed by Grafana's frontend and not available via API
GRAFANA_BUILTINS = {
    "__rate_interval": "5m",
    "__interval": "1m",
    "__interval_ms": "60000",
    "__range": "1h",
    "__range_s": "3600",
    "__range_ms": "3600000",
}


def _substitute_variables(obj: Any, variables: dict[str, Any]) -> Any:
    """Recursively substitute ${varname} and $varname patterns in strings."""
    # Merge Grafana built-ins with user variables (user vars take precedence)
    all_vars = {**GRAFANA_BUILTINS, **(variables or {})}
    if not all_vars:
        return obj
    if isinstance(obj, str):
        for name, value in all_vars.items():
            obj = obj.replace(f"${{{name}}}", str(value))
            obj = obj.replace(f"${name}", str(value))  # Also handle $varname
        return obj
    elif isinstance(obj, dict):
        return {k: _substitute_variables(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_variables(item, variables) for item in obj]
    return obj


class GrafanaClient:
    """HTTP client for interacting with Grafana API."""

    def __init__(
        self,
        url: str,
        api_key: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize the Grafana client.

        Args:
            url: Base URL of Grafana instance (e.g., https://grafana.example.com)
            api_key: Grafana API key or service account token
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = url.rstrip("/")
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
            verify=verify_ssl,
        )

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to Grafana API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /api/dashboards/uid/xxx)
            **kwargs: Additional arguments to pass to httpx

        Returns:
            JSON response as dictionary

        Raises:
            GrafanaAuthError: If authentication fails
            GrafanaNotFoundError: If resource not found
            GrafanaAPIError: For other API errors
            GrafanaConnectionError: If connection fails
        """
        url = f"{self.base_url}{path}"

        try:
            response = self._client.request(method, url, **kwargs)
        except httpx.ConnectError as e:
            raise GrafanaConnectionError(f"Failed to connect to {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise GrafanaConnectionError(f"Request to {url} timed out")

        if response.status_code == 401:
            raise GrafanaAuthError("Invalid or expired API key")
        if response.status_code == 403:
            raise GrafanaAuthError("API key does not have permission for this operation")
        if response.status_code == 404:
            raise GrafanaNotFoundError(f"Resource not found: {path}")
        if not response.is_success:
            raise GrafanaAPIError(
                f"Grafana API error: {response.status_code} - {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    def get_dashboard(self, uid: str) -> Dashboard:
        """
        Fetch a dashboard by UID.

        Args:
            uid: Dashboard UID

        Returns:
            Dashboard object

        Raises:
            GrafanaNotFoundError: If dashboard not found
        """
        response = self._request("GET", f"/api/dashboards/uid/{uid}")
        return Dashboard.from_api_response(response)

    def get_panel(self, dashboard_uid: str, panel_id: int) -> Panel:
        """
        Get a specific panel from a dashboard.

        Args:
            dashboard_uid: Dashboard UID
            panel_id: Panel ID within the dashboard

        Returns:
            Panel object

        Raises:
            GrafanaNotFoundError: If dashboard or panel not found
        """
        dashboard = self.get_dashboard(dashboard_uid)
        panel = dashboard.get_panel_by_id(panel_id)

        if panel is None:
            raise GrafanaNotFoundError(
                f"Panel {panel_id} not found in dashboard {dashboard_uid}"
            )

        return panel

    def query_datasource(
        self,
        queries: list[dict[str, Any]],
        time_from: str = "now-1h",
        time_to: str = "now",
    ) -> QueryResult:
        """
        Execute queries against a datasource.

        Args:
            queries: List of query targets (from panel.targets)
            time_from: Start of time range (e.g., "now-1h", "now-6h")
            time_to: End of time range (e.g., "now")

        Returns:
            QueryResult with data frames
        """
        if not queries:
            return QueryResult()

        # Log datasource info for debugging
        for i, q in enumerate(queries):
            ds = q.get("datasource", {})
            logger.info(f"Query {i}: datasource={ds}, refId={q.get('refId')}")

        # Build query payload
        payload = {
            "from": time_from,
            "to": time_to,
            "queries": queries,
        }

        response = self._request("POST", "/api/ds/query", json=payload)
        return QueryResult.from_api_response(response)

    def query_panel(
        self,
        panel: Panel,
        time_from: str = "now-1h",
        time_to: str = "now",
        variables: dict[str, Any] | None = None,
    ) -> QueryResult:
        """
        Execute a panel's queries.

        Args:
            panel: Panel object with targets
            time_from: Start of time range
            time_to: End of time range
            variables: Dict of Grafana variables to substitute (e.g., {"datasource": "uid"})

        Returns:
            QueryResult with data frames
        """
        variables = variables or {}
        logger.info(f"Panel datasource: {panel.datasource}")
        logger.info(f"Panel has {len(panel.targets)} targets")
        if variables:
            logger.info(f"Variables to substitute: {variables}")

        queries = []
        for target in panel.targets:
            query = target.copy()
            # If target doesn't have datasource, use panel's datasource
            if "datasource" not in query or not query.get("datasource"):
                if panel.datasource:
                    query["datasource"] = panel.datasource
            # Substitute variables in the entire query
            query = _substitute_variables(query, variables)
            logger.info(f"Query after substitution: {query}")
            queries.append(query)

        return self.query_datasource(queries, time_from, time_to)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "GrafanaClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
