"""Tests for TRMNL webhook client."""

import pytest
from unittest.mock import patch, MagicMock, Mock
import httpx

from service.trmnl import TRMNLClient, TRMNLError


class TestTRMNLClientInit:
    """Tests for TRMNLClient initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default timeout."""
        client = TRMNLClient("https://webhook.trmnl.com/xxx")
        assert client.webhook_url == "https://webhook.trmnl.com/xxx"
        assert client.timeout == 30.0

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = TRMNLClient("https://webhook.trmnl.com/xxx", timeout=60.0)
        assert client.timeout == 60.0


class TestTRMNLClientSend:
    """Tests for TRMNLClient.send method."""

    @patch("httpx.Client")
    def test_send_success(self, mock_client_class):
        """Test successful send."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")
        result = client.send({"panel_type": "stat", "value": 42})

        assert result is True
        mock_http_client.post.assert_called_once_with(
            "https://webhook.trmnl.com/xxx",
            json={"merge_variables": {"panel_type": "stat", "value": 42}},
            headers={"Content-Type": "application/json"},
        )

    @patch("httpx.Client")
    def test_send_error_response(self, mock_client_class):
        """Test send with error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid payload"}

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")

        with pytest.raises(TRMNLError) as exc_info:
            client.send({"panel_type": "stat"})

        assert "400" in str(exc_info.value)
        assert "Invalid payload" in str(exc_info.value)

    @patch("httpx.Client")
    def test_send_error_response_non_json(self, mock_client_class):
        """Test send with error response that's not JSON."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Internal Server Error"

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")

        with pytest.raises(TRMNLError) as exc_info:
            client.send({"panel_type": "stat"})

        assert "500" in str(exc_info.value)
        assert "Internal Server Error" in str(exc_info.value)

    @patch("httpx.Client")
    def test_send_timeout(self, mock_client_class):
        """Test send with timeout."""
        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = httpx.TimeoutException("Timed out")
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx", timeout=10.0)

        with pytest.raises(TRMNLError) as exc_info:
            client.send({"panel_type": "stat"})

        assert "timed out" in str(exc_info.value)

    @patch("httpx.Client")
    def test_send_request_error(self, mock_client_class):
        """Test send with request error."""
        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")

        with pytest.raises(TRMNLError) as exc_info:
            client.send({"panel_type": "stat"})

        assert "request failed" in str(exc_info.value).lower()


class TestTRMNLClientSendError:
    """Tests for TRMNLClient.send_error method."""

    @patch("httpx.Client")
    def test_send_error_basic(self, mock_client_class):
        """Test sending error state."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")
        result = client.send_error("Connection failed")

        assert result is True

        # Verify the payload structure
        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]["merge_variables"]
        assert payload["panel_type"] == "error"
        assert payload["error_message"] == "Connection failed"
        assert payload["title"] == "Error"

    @patch("httpx.Client")
    def test_send_error_with_title(self, mock_client_class):
        """Test sending error state with custom title."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__enter__ = Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_http_client

        client = TRMNLClient("https://webhook.trmnl.com/xxx")
        result = client.send_error("API timeout", title="Grafana Error")

        assert result is True

        call_args = mock_http_client.post.call_args
        payload = call_args[1]["json"]["merge_variables"]
        assert payload["title"] == "Grafana Error"
        assert payload["error_message"] == "API timeout"


class TestTRMNLError:
    """Tests for TRMNLError exception."""

    def test_error_message(self):
        """Test TRMNLError stores message."""
        error = TRMNLError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Test TRMNLError inherits from Exception."""
        error = TRMNLError("Test")
        assert isinstance(error, Exception)
