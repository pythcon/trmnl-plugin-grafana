"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from service.config import Config, ConfigError, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_creation(self):
        """Test creating a Config object."""
        config = Config(
            grafana_url="https://grafana.example.com",
            grafana_api_key="test-key",
            dashboard_uid="abc123",
            panel_id=1,
            time_from="now-1h",
            time_to="now",
            trmnl_webhook_url="https://webhook.trmnl.com/xxx",
            interval=300,
            label="name",
            timezone="UTC",
        )

        assert config.grafana_url == "https://grafana.example.com"
        assert config.grafana_api_key == "test-key"
        assert config.dashboard_uid == "abc123"
        assert config.panel_id == 1
        assert config.time_from == "now-1h"
        assert config.time_to == "now"
        assert config.trmnl_webhook_url == "https://webhook.trmnl.com/xxx"
        assert config.interval == 300
        assert config.label == "name"


class TestLoadConfig:
    """Tests for load_config function."""

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_minimal(self, mock_load_dotenv):
        """Test loading config with minimal required env vars."""
        config = load_config()

        assert config.grafana_url == "https://grafana.example.com"
        assert config.grafana_api_key == "test-api-key"
        assert config.dashboard_uid == "dashboard123"
        assert config.panel_id == 42
        assert config.trmnl_webhook_url == "https://webhook.trmnl.com/xxx"
        # Defaults
        assert config.time_from == "now-1h"
        assert config.time_to == "now"
        assert config.interval == 300

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com/",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
        "TIME_FROM": "now-6h",
        "TIME_TO": "now-1h",
        "INTERVAL": "600",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_all_options(self, mock_load_dotenv):
        """Test loading config with all env vars."""
        config = load_config()

        assert config.grafana_url == "https://grafana.example.com"  # Trailing slash stripped
        assert config.time_from == "now-6h"
        assert config.time_to == "now-1h"
        assert config.interval == 600

    @patch.dict(os.environ, {}, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_missing_all_required(self, mock_load_dotenv):
        """Test loading config with all required vars missing."""
        with pytest.raises(ConfigError) as exc_info:
            load_config()

        error_msg = str(exc_info.value)
        assert "GRAFANA_URL is required" in error_msg
        assert "GRAFANA_API_KEY is required" in error_msg
        assert "DASHBOARD_UID is required" in error_msg
        assert "PANEL_ID is required" in error_msg
        assert "TRMNL_WEBHOOK_URL is required" in error_msg

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        # Missing TRMNL_WEBHOOK_URL
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_missing_webhook_url(self, mock_load_dotenv):
        """Test loading config with missing webhook URL."""
        with pytest.raises(ConfigError) as exc_info:
            load_config()

        assert "TRMNL_WEBHOOK_URL is required" in str(exc_info.value)

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "not-a-number",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_invalid_panel_id(self, mock_load_dotenv):
        """Test loading config with non-integer panel ID."""
        with pytest.raises(ConfigError) as exc_info:
            load_config()

        assert "PANEL_ID must be an integer" in str(exc_info.value)
        assert "not-a-number" in str(exc_info.value)

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
        "INTERVAL": "not-a-number",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_invalid_interval_uses_default(self, mock_load_dotenv):
        """Test that invalid interval falls back to default."""
        config = load_config()
        assert config.interval == 300

    @patch.dict(os.environ, {
        "GRAFANA_URL": "",
        "GRAFANA_API_KEY": "test-api-key",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_empty_url(self, mock_load_dotenv):
        """Test loading config with empty URL."""
        with pytest.raises(ConfigError) as exc_info:
            load_config()

        assert "GRAFANA_URL is required" in str(exc_info.value)

    @patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "",
        "DASHBOARD_UID": "dashboard123",
        "PANEL_ID": "42",
        "TRMNL_WEBHOOK_URL": "https://webhook.trmnl.com/xxx",
    }, clear=True)
    @patch("service.config.load_dotenv")
    def test_load_config_empty_api_key(self, mock_load_dotenv):
        """Test loading config with empty API key."""
        with pytest.raises(ConfigError) as exc_info:
            load_config()

        assert "GRAFANA_API_KEY is required" in str(exc_info.value)


class TestConfigError:
    """Tests for ConfigError exception."""

    def test_config_error_message(self):
        """Test ConfigError stores and displays message."""
        error = ConfigError("Test configuration error")
        assert str(error) == "Test configuration error"

    def test_config_error_inheritance(self):
        """Test ConfigError inherits from Exception."""
        error = ConfigError("Test")
        assert isinstance(error, Exception)
