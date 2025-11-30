#!/usr/bin/env python3
"""Main entry point for the TRMNL Grafana data service."""

import logging
import sys
import time
from typing import NoReturn

from service.config import Config, ConfigError, load_config
from service.grafana import GrafanaClient, GrafanaAPIError
from service.transformers import get_transformer
from service.trmnl import TRMNLClient, TRMNLError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_and_send(config: Config) -> bool:
    """
    Fetch data from Grafana and send to TRMNL.

    Args:
        config: Service configuration

    Returns:
        True if successful, False otherwise
    """
    grafana = GrafanaClient(config.grafana_url, config.grafana_api_key)
    trmnl = TRMNLClient(config.trmnl_webhook_url)

    try:
        # Get dashboard and panel
        logger.info(f"Fetching dashboard {config.dashboard_uid}, panel {config.panel_id}")
        dashboard = grafana.get_dashboard(config.dashboard_uid)
        panel = dashboard.get_panel_by_id(config.panel_id)

        if panel is None:
            error_msg = f"Panel {config.panel_id} not found in dashboard"
            logger.error(error_msg)
            trmnl.send_error(error_msg, "Configuration Error")
            return False

        logger.info(f"Found panel: {panel.title} (type: {panel.type})")

        # Query panel data
        query_result = grafana.query_panel(
            panel,
            time_from=config.time_from,
            time_to=config.time_to,
        )

        if query_result.error:
            logger.error(f"Query error: {query_result.error}")
            trmnl.send_error(query_result.error, panel.title)
            return False

        # Transform data for TRMNL
        transformer = get_transformer(panel.type)
        logger.info(f"Using transformer: {transformer.__class__.__name__}")

        merge_variables = transformer.transform(panel, query_result, label_key=config.label)

        # Send to TRMNL
        trmnl.send(merge_variables)
        return True

    except GrafanaAPIError as e:
        logger.error(f"Grafana error: {e}")
        try:
            trmnl.send_error(str(e), "Grafana Error")
        except TRMNLError:
            pass
        return False

    except TRMNLError as e:
        logger.error(f"TRMNL error: {e}")
        return False

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        try:
            trmnl.send_error(f"Internal error: {type(e).__name__}", "Error")
        except TRMNLError:
            pass
        return False


def run_once(config: Config) -> int:
    """
    Run a single fetch-and-send cycle.

    Args:
        config: Service configuration

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    success = fetch_and_send(config)
    return 0 if success else 1


def run_loop(config: Config) -> NoReturn:
    """
    Run continuous fetch-and-send loop.

    Args:
        config: Service configuration
    """
    logger.info(f"Starting continuous mode with {config.interval}s interval")

    while True:
        fetch_and_send(config)
        logger.info(f"Sleeping for {config.interval} seconds...")
        time.sleep(config.interval)


def main() -> int:
    """Main entry point."""
    logger.info("TRMNL Grafana Data Service starting...")

    try:
        config = load_config()
    except ConfigError as e:
        logger.error(f"Configuration error:\n{e}")
        return 1

    logger.info(f"Configured for dashboard={config.dashboard_uid}, panel={config.panel_id}")
    logger.info(f"Time range: {config.time_from} to {config.time_to}")

    # Check for run mode
    if "--once" in sys.argv:
        return run_once(config)
    else:
        run_loop(config)


if __name__ == "__main__":
    sys.exit(main())
