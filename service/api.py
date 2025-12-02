"""Flask API for Polling strategy - TRMNL fetches data from this endpoint.

Supports two modes:
1. Environment variables: Set GRAFANA_URL, GRAFANA_API_KEY, etc. and use GET requests
2. POST body: Send configuration in JSON body (falls back to env vars for missing fields)
"""

import json
import logging
import os
from flask import Flask, jsonify, request

from service.grafana import GrafanaClient, GrafanaAPIError
from service.transformers import get_transformer
from service.test_data import TEST_DATA, PANEL_ALIASES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_config_from_request():
    """
    Extract configuration from POST body, falling back to environment variables.

    Returns:
        tuple: (config_dict, errors_list)
    """
    # Get POST body if available
    if request.method == "POST" and request.is_json:
        body = request.get_json() or {}
    else:
        body = {}

    # Parse variables (can be dict or JSON string)
    variables = body.get("variables", {})
    if isinstance(variables, str):
        try:
            variables = json.loads(variables) if variables else {}
        except json.JSONDecodeError:
            variables = {}

    # Merge: POST body takes precedence over env vars
    config = {
        "grafana_url": (body.get("grafana_url") or os.environ.get("GRAFANA_URL", "")).rstrip("/"),
        "api_key": body.get("api_key") or os.environ.get("GRAFANA_API_KEY", ""),
        "dashboard_uid": body.get("dashboard_uid") or os.environ.get("DASHBOARD_UID", ""),
        "panel_id": body.get("panel_id") or os.environ.get("PANEL_ID", ""),
        "time_from": body.get("time_from") or os.environ.get("TIME_FROM", "now-1h"),
        "time_to": body.get("time_to") or os.environ.get("TIME_TO", "now"),
        "label": body.get("label") or os.environ.get("LABEL", "name"),
        "timezone": body.get("timezone") or os.environ.get("TIMEZONE", "UTC"),
        "variables": variables,
    }

    # Validate required fields
    errors = []
    if not config["grafana_url"]:
        errors.append("grafana_url is required")
    if not config["api_key"]:
        errors.append("api_key is required")
    if not config["dashboard_uid"]:
        errors.append("dashboard_uid is required")
    if not config["panel_id"]:
        errors.append("panel_id is required")

    # Convert panel_id to int
    if config["panel_id"] and not errors:
        try:
            config["panel_id"] = int(config["panel_id"])
        except (ValueError, TypeError):
            errors.append("panel_id must be an integer")

    return config, errors


@app.route("/", methods=["GET", "POST"])
@app.route("/api/data", methods=["GET", "POST"])
def get_data():
    """
    Endpoint TRMNL polls for data.

    Accepts GET (uses env vars) or POST with JSON body:
    {
        "grafana_url": "https://grafana.example.com",
        "api_key": "glsa_xxxxxxxxxxxx",
        "dashboard_uid": "abc123",
        "panel_id": 1,
        "time_from": "now-1h",
        "time_to": "now"
    }

    Returns merge_variables JSON that TRMNL uses with Liquid templates.
    """
    # Get config from request body or env vars
    config, errors = get_config_from_request()

    logger.info(f"Request: dashboard={config.get('dashboard_uid')}, panel={config.get('panel_id')}, time={config.get('time_from')} to {config.get('time_to')}")

    if errors:
        return jsonify({
            "error": "Missing or invalid configuration",
            "details": errors,
        }), 400

    try:
        with GrafanaClient(config["grafana_url"], config["api_key"]) as client:
            dashboard = client.get_dashboard(config["dashboard_uid"])
            logger.info(f"Dashboard '{dashboard.title}' has {len(dashboard.panels)} panels")

            panel = dashboard.get_panel_by_id(config["panel_id"])

            if panel is None:
                available = [(p.id, p.type, p.title) for p in dashboard.panels]
                logger.error(f"Panel {config['panel_id']} not found. Available: {available}")
                return jsonify({
                    "panel_type": "error",
                    "error_message": f"Panel {config['panel_id']} not found in dashboard",
                }), 404

            result = client.query_panel(
                panel, config["time_from"], config["time_to"],
                variables=config.get("variables", {})
            )
            logger.info(f"Query returned {len(result.frames)} frames for panel '{panel.title}' (type: {panel.type})")
            for i, frame in enumerate(result.frames):
                logger.debug(f"Frame {i}: name={frame.name}, {len(frame.fields)} fields, {len(frame.values) if frame.values else 0} value columns")

            # Debug logging for timeseries panels to see field structure
            if panel.type == "timeseries":
                for i, frame in enumerate(result.frames):
                    logger.info(f"Frame {i} fields: {frame.fields}")
                    logger.info(f"Frame {i} values: {len(frame.values)} columns")

            # Debug logging for table panels
            if panel.type == "table":
                for i, frame in enumerate(result.frames):
                    logger.info(f"Table frame {i}: fields={frame.fields}")
                    logger.info(f"Table frame {i}: values count={len(frame.values) if frame.values else 0}")

            if result.error:
                logger.error(f"Query error: {result.error}")
                return jsonify({
                    "panel_type": "error",
                    "title": panel.title,
                    "error_message": result.error,
                }), 500

        transformer = get_transformer(panel.type)
        logger.info(f"Using transformer: {transformer.__class__.__name__}")
        merge_variables = transformer.transform(panel, result, label_key=config["label"], timezone=config["timezone"])

        logger.info(f"Transform output keys: {list(merge_variables.keys())}")
        if "stats" in merge_variables:
            logger.info(f"Stats count: {len(merge_variables['stats'])}")
        logger.info(f"Returning data for {panel.type} panel: {panel.title}")
        return jsonify(merge_variables)

    except GrafanaAPIError as e:
        logger.error(f"Grafana error: {e}")
        return jsonify({
            "panel_type": "error",
            "error_message": str(e),
        }), 502

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return jsonify({
            "panel_type": "error",
            "error_message": f"Internal error: {type(e).__name__}",
        }), 500


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/api/test/<panel_type>", methods=["GET", "POST"])
def get_test_data(panel_type: str):
    """
    Return test/demonstration data for a panel type.

    Supported types: stat, gauge, bargauge, polystat, table, timeseries
    """
    panel_type = panel_type.lower()
    panel_type = PANEL_ALIASES.get(panel_type, panel_type)

    if panel_type not in TEST_DATA:
        return jsonify({
            "error": f"Unknown panel type: {panel_type}",
            "available_types": list(TEST_DATA.keys()),
        }), 404

    return jsonify(TEST_DATA[panel_type])


def create_app():
    """Application factory for gunicorn."""
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
