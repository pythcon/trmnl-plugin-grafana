"""Tests for Grafana HTTP client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from service.grafana.client import GrafanaClient
from service.grafana.exceptions import (
    GrafanaAPIError,
    GrafanaAuthError,
    GrafanaNotFoundError,
    GrafanaConnectionError,
)
from service.grafana.models import Dashboard, Panel, QueryResult


class TestGrafanaClientInit:
    """Tests for GrafanaClient initialization."""

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        client = GrafanaClient("https://grafana.example.com/", "test-key")
        assert client.base_url == "https://grafana.example.com"
        client.close()

    def test_init_preserves_url_without_slash(self):
        """Test URL without trailing slash is preserved."""
        client = GrafanaClient("https://grafana.example.com", "test-key")
        assert client.base_url == "https://grafana.example.com"
        client.close()


class TestGrafanaClientRequest:
    """Tests for GrafanaClient._request method."""

    @patch("httpx.Client")
    def test_request_success(self, mock_client_class):
        """Test successful request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"result": "success"}

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        result = client._request("GET", "/api/test")

        assert result == {"result": "success"}
        mock_client.request.assert_called_once_with(
            "GET", "https://grafana.example.com/api/test"
        )

    @patch("httpx.Client")
    def test_request_401_raises_auth_error(self, mock_client_class):
        """Test 401 response raises GrafanaAuthError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.is_success = False

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaAuthError) as exc_info:
            client._request("GET", "/api/test")

        assert "Invalid or expired API key" in str(exc_info.value)

    @patch("httpx.Client")
    def test_request_403_raises_auth_error(self, mock_client_class):
        """Test 403 response raises GrafanaAuthError."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.is_success = False

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaAuthError) as exc_info:
            client._request("GET", "/api/test")

        assert "permission" in str(exc_info.value).lower()

    @patch("httpx.Client")
    def test_request_404_raises_not_found_error(self, mock_client_class):
        """Test 404 response raises GrafanaNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.is_success = False

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaNotFoundError) as exc_info:
            client._request("GET", "/api/dashboards/uid/missing")

        assert "not found" in str(exc_info.value).lower()

    @patch("httpx.Client")
    def test_request_500_raises_api_error(self, mock_client_class):
        """Test 500 response raises GrafanaAPIError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.is_success = False
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaAPIError) as exc_info:
            client._request("GET", "/api/test")

        assert exc_info.value.status_code == 500

    @patch("httpx.Client")
    def test_request_connect_error(self, mock_client_class):
        """Test connection error raises GrafanaConnectionError."""
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaConnectionError) as exc_info:
            client._request("GET", "/api/test")

        assert "Failed to connect" in str(exc_info.value)

    @patch("httpx.Client")
    def test_request_timeout_error(self, mock_client_class):
        """Test timeout raises GrafanaConnectionError."""
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaConnectionError) as exc_info:
            client._request("GET", "/api/test")

        assert "timed out" in str(exc_info.value)


class TestGrafanaClientDashboard:
    """Tests for GrafanaClient dashboard methods."""

    @patch("httpx.Client")
    def test_get_dashboard(self, mock_client_class, grafana_dashboard_response: dict):
        """Test fetching a dashboard."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = grafana_dashboard_response

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        dashboard = client.get_dashboard("abc123")

        assert isinstance(dashboard, Dashboard)
        assert dashboard.uid == "abc123"
        assert dashboard.title == "Production Metrics"

        mock_client.request.assert_called_once_with(
            "GET", "https://grafana.example.com/api/dashboards/uid/abc123"
        )

    @patch("httpx.Client")
    def test_get_panel(self, mock_client_class, grafana_dashboard_response: dict):
        """Test fetching a specific panel."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = grafana_dashboard_response

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        panel = client.get_panel("abc123", 1)

        assert isinstance(panel, Panel)
        assert panel.id == 1
        assert panel.type == "stat"
        assert panel.title == "CPU Usage"

    @patch("httpx.Client")
    def test_get_panel_not_found(self, mock_client_class, grafana_dashboard_response: dict):
        """Test fetching non-existent panel."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = grafana_dashboard_response

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")

        with pytest.raises(GrafanaNotFoundError) as exc_info:
            client.get_panel("abc123", 999)

        assert "Panel 999 not found" in str(exc_info.value)


class TestGrafanaClientQuery:
    """Tests for GrafanaClient query methods."""

    @patch("httpx.Client")
    def test_query_datasource(self, mock_client_class, grafana_query_response: dict):
        """Test querying a datasource."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = grafana_query_response

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        queries = [{"refId": "A", "expr": "cpu_usage"}]
        result = client.query_datasource(queries, "now-1h", "now")

        assert isinstance(result, QueryResult)
        assert len(result.frames) == 1

        # Verify POST was called with correct payload
        call_args = mock_client.request.call_args
        assert call_args[0] == ("POST", "https://grafana.example.com/api/ds/query")
        payload = call_args[1]["json"]
        assert payload["from"] == "now-1h"
        assert payload["to"] == "now"
        assert payload["queries"] == queries

    @patch("httpx.Client")
    def test_query_datasource_empty_queries(self, mock_client_class):
        """Test querying with empty queries returns empty result."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        result = client.query_datasource([], "now-1h", "now")

        assert isinstance(result, QueryResult)
        assert len(result.frames) == 0
        mock_client.request.assert_not_called()

    @patch("httpx.Client")
    def test_query_panel(self, mock_client_class, grafana_query_response: dict):
        """Test querying a panel."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = grafana_query_response

        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        panel = Panel(
            id=1,
            type="stat",
            title="Test",
            targets=[{"refId": "A", "expr": "cpu_usage"}],
        )

        client = GrafanaClient("https://grafana.example.com", "test-key")
        result = client.query_panel(panel, "now-6h", "now")

        assert isinstance(result, QueryResult)

        # Verify query was made with panel targets
        call_args = mock_client.request.call_args
        payload = call_args[1]["json"]
        assert payload["queries"] == panel.targets


class TestGrafanaClientContextManager:
    """Tests for GrafanaClient context manager."""

    @patch("httpx.Client")
    def test_context_manager(self, mock_client_class):
        """Test client can be used as context manager."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        with GrafanaClient("https://grafana.example.com", "test-key") as client:
            assert isinstance(client, GrafanaClient)

        mock_client.close.assert_called_once()

    @patch("httpx.Client")
    def test_close(self, mock_client_class):
        """Test explicit close."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = GrafanaClient("https://grafana.example.com", "test-key")
        client.close()

        mock_client.close.assert_called_once()


class TestGrafanaExceptions:
    """Tests for Grafana exception classes."""

    def test_api_error_with_status_code(self):
        """Test GrafanaAPIError stores status code."""
        error = GrafanaAPIError("Test error", status_code=500)
        assert error.message == "Test error"
        assert error.status_code == 500
        assert str(error) == "Test error"

    def test_api_error_without_status_code(self):
        """Test GrafanaAPIError without status code."""
        error = GrafanaAPIError("Test error")
        assert error.status_code is None

    def test_auth_error_default_message(self):
        """Test GrafanaAuthError default message."""
        error = GrafanaAuthError()
        assert "Invalid or expired API key" in str(error)
        assert error.status_code == 401

    def test_not_found_error_default_message(self):
        """Test GrafanaNotFoundError default message."""
        error = GrafanaNotFoundError()
        assert "not found" in str(error).lower()
        assert error.status_code == 404

    def test_connection_error_default_message(self):
        """Test GrafanaConnectionError default message."""
        error = GrafanaConnectionError()
        assert "Failed to connect" in str(error)
