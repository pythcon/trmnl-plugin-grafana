"""Tests for Flask API endpoint."""

import os
import pytest
from unittest.mock import patch, MagicMock

from service.api import app, get_config_from_request


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestGetConfigFromRequest:
    """Tests for get_config_from_request helper."""

    def test_config_from_post_body(self, client):
        """Test config extracted from POST body."""
        with app.test_request_context(
            "/api/data",
            method="POST",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 1,
            },
        ):
            config, errors = get_config_from_request()

            assert errors == []
            assert config["grafana_url"] == "https://grafana.example.com"
            assert config["api_key"] == "test-key"
            assert config["dashboard_uid"] == "abc123"
            assert config["panel_id"] == 1
            assert config["time_from"] == "now-1h"  # default
            assert config["time_to"] == "now"  # default

    def test_config_from_env_vars(self, client):
        """Test config extracted from environment variables."""
        with patch.dict(os.environ, {
            "GRAFANA_URL": "https://env-grafana.example.com",
            "GRAFANA_API_KEY": "env-key",
            "DASHBOARD_UID": "env-dashboard",
            "PANEL_ID": "42",
        }, clear=True):
            with app.test_request_context("/api/data", method="GET"):
                config, errors = get_config_from_request()

                assert errors == []
                assert config["grafana_url"] == "https://env-grafana.example.com"
                assert config["api_key"] == "env-key"
                assert config["dashboard_uid"] == "env-dashboard"
                assert config["panel_id"] == 42

    def test_post_body_overrides_env_vars(self, client):
        """Test POST body takes precedence over env vars."""
        with patch.dict(os.environ, {
            "GRAFANA_URL": "https://env-grafana.example.com",
            "GRAFANA_API_KEY": "env-key",
            "DASHBOARD_UID": "env-dashboard",
            "PANEL_ID": "1",
        }, clear=True):
            with app.test_request_context(
                "/api/data",
                method="POST",
                json={
                    "grafana_url": "https://post-grafana.example.com",
                    "api_key": "post-key",
                    # dashboard_uid and panel_id not in body - should use env
                },
            ):
                config, errors = get_config_from_request()

                assert errors == []
                assert config["grafana_url"] == "https://post-grafana.example.com"
                assert config["api_key"] == "post-key"
                assert config["dashboard_uid"] == "env-dashboard"  # from env
                assert config["panel_id"] == 1  # from env

    def test_missing_required_fields(self, client):
        """Test validation errors for missing fields."""
        with patch.dict(os.environ, {}, clear=True):
            with app.test_request_context("/api/data", method="GET"):
                config, errors = get_config_from_request()

                assert "grafana_url is required" in errors
                assert "api_key is required" in errors
                assert "dashboard_uid is required" in errors
                assert "panel_id is required" in errors

    def test_invalid_panel_id(self, client):
        """Test validation error for non-integer panel_id."""
        with app.test_request_context(
            "/api/data",
            method="POST",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": "not-a-number",
            },
        ):
            config, errors = get_config_from_request()

            assert "panel_id must be an integer" in errors

    def test_trailing_slash_stripped(self, client):
        """Test trailing slash is stripped from grafana_url."""
        with app.test_request_context(
            "/api/data",
            method="POST",
            json={
                "grafana_url": "https://grafana.example.com/",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 1,
            },
        ):
            config, errors = get_config_from_request()

            assert config["grafana_url"] == "https://grafana.example.com"

    def test_custom_time_range(self, client):
        """Test custom time range from POST body."""
        with app.test_request_context(
            "/api/data",
            method="POST",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 1,
                "time_from": "now-24h",
                "time_to": "now-1h",
            },
        ):
            config, errors = get_config_from_request()

            assert config["time_from"] == "now-24h"
            assert config["time_to"] == "now-1h"


class TestApiDataEndpoint:
    """Tests for /api/data endpoint."""

    def test_post_missing_config_returns_400(self, client):
        """Test POST with missing config returns 400."""
        response = client.post(
            "/api/data",
            json={},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "details" in data
        assert len(data["details"]) > 0

    def test_get_missing_env_returns_400(self, client):
        """Test GET with no env vars returns 400."""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get("/api/data")

            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data

    @patch("service.api.GrafanaClient")
    def test_post_success(self, mock_client_class, client):
        """Test successful POST request."""
        # Setup mocks
        mock_panel = MagicMock()
        mock_panel.type = "stat"
        mock_panel.title = "Test Panel"
        mock_panel.description = ""
        mock_panel.get_unit.return_value = ""
        mock_panel.get_decimals.return_value = None
        mock_panel.get_thresholds.return_value = []

        mock_dashboard = MagicMock()
        mock_dashboard.get_panel_by_id.return_value = mock_panel

        mock_query_result = MagicMock()
        mock_query_result.error = None
        mock_query_result.get_single_value.return_value = 42.5
        mock_query_result.frames = []

        mock_grafana = MagicMock()
        mock_grafana.get_dashboard.return_value = mock_dashboard
        mock_grafana.query_panel.return_value = mock_query_result
        mock_grafana.__enter__ = MagicMock(return_value=mock_grafana)
        mock_grafana.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_grafana

        response = client.post(
            "/api/data",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 1,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["panel_type"] == "stat"
        assert data["title"] == "Test Panel"

    @patch("service.api.GrafanaClient")
    def test_panel_not_found_returns_404(self, mock_client_class, client):
        """Test 404 when panel not found."""
        mock_dashboard = MagicMock()
        mock_dashboard.get_panel_by_id.return_value = None

        mock_grafana = MagicMock()
        mock_grafana.get_dashboard.return_value = mock_dashboard
        mock_grafana.__enter__ = MagicMock(return_value=mock_grafana)
        mock_grafana.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_grafana

        response = client.post(
            "/api/data",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 999,
            },
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["panel_type"] == "error"
        assert "not found" in data["error_message"]

    @patch("service.api.GrafanaClient")
    def test_grafana_error_returns_502(self, mock_client_class, client):
        """Test 502 when Grafana returns error."""
        from service.grafana.exceptions import GrafanaAPIError

        mock_grafana = MagicMock()
        mock_grafana.get_dashboard.side_effect = GrafanaAPIError("Connection failed")
        mock_grafana.__enter__ = MagicMock(return_value=mock_grafana)
        mock_grafana.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_grafana

        response = client.post(
            "/api/data",
            json={
                "grafana_url": "https://grafana.example.com",
                "api_key": "test-key",
                "dashboard_uid": "abc123",
                "panel_id": 1,
            },
            content_type="application/json",
        )

        assert response.status_code == 502
        data = response.get_json()
        assert data["panel_type"] == "error"


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Test health check returns OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}
