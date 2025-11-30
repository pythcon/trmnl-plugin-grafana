"""TRMNL webhook client for sending merge_variables."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TRMNLError(Exception):
    """Raised when TRMNL webhook request fails."""

    pass


class TRMNLClient:
    """Client for sending data to TRMNL webhook."""

    def __init__(self, webhook_url: str, timeout: float = 30.0):
        """
        Initialize TRMNL client.

        Args:
            webhook_url: Full webhook URL from TRMNL plugin settings
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, merge_variables: dict[str, Any]) -> bool:
        """
        Send merge_variables to TRMNL webhook.

        Args:
            merge_variables: Dictionary of template variables

        Returns:
            True if successful

        Raises:
            TRMNLError: If the request fails
        """
        payload = {"merge_variables": merge_variables}

        logger.info(f"Sending data to TRMNL webhook: {len(merge_variables)} variables")
        logger.debug(f"Payload: {payload}")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code == 200:
                logger.info("Successfully sent data to TRMNL")
                return True

            # Handle error responses
            error_msg = f"TRMNL webhook returned {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = f"{error_msg}: {error_data['error']}"
            except Exception:
                error_msg = f"{error_msg}: {response.text[:200]}"

            logger.error(error_msg)
            raise TRMNLError(error_msg)

        except httpx.TimeoutException:
            error_msg = f"TRMNL webhook request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise TRMNLError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"TRMNL webhook request failed: {e}"
            logger.error(error_msg)
            raise TRMNLError(error_msg)

    def send_error(self, error_message: str, title: str = "Error") -> bool:
        """
        Send an error state to TRMNL.

        Args:
            error_message: Error description
            title: Panel title

        Returns:
            True if successful
        """
        return self.send({
            "panel_type": "error",
            "title": title,
            "error_message": error_message,
        })
