"""Test/demonstration data for each panel type."""

TEST_DATA = {
    "stat": {
        "panel_type": "stat",
        "title": "Active Users",
        "description": "Currently online",
        "timestamp": "2025-11-30 12:00 UTC",
        "value": 1247,
        "formatted_value": "1,247",
        "color": "green",
    },
    "gauge": {
        "panel_type": "gauge",
        "title": "Memory Usage",
        "timestamp": "2025-11-30 12:00 UTC",
        "value": 68,
        "formatted_value": "68%",
        "percentage": 68,
        "min": 0,
        "max": 100,
        "color": "yellow",
    },
    "bargauge": {
        "panel_type": "bargauge",
        "title": "System Pressure",
        "timestamp": "2025-12-01 12:00 UTC",
        "bars": [
            {"name": "cpu", "value": 45.2, "formatted_value": "45.2%", "percentage": 45, "color": "green"},
            {"name": "memory", "value": 72.8, "formatted_value": "72.8%", "percentage": 73, "color": "yellow"},
            {"name": "io", "value": 12.5, "formatted_value": "12.5%", "percentage": 13, "color": "green"},
        ],
    },
    "polystat": {
        "panel_type": "polystat",
        "title": "Service Health",
        "timestamp": "2025-11-30 12:00 UTC",
        "stats": [
            {"name": "API Gateway", "value": 99.9, "formatted_value": "99.9%", "status": "ok"},
            {"name": "Auth Service", "value": 100, "formatted_value": "100%", "status": "ok"},
            {"name": "Database", "value": 98.5, "formatted_value": "98.5%", "status": "ok"},
            {"name": "Cache", "value": 85.2, "formatted_value": "85.2%", "status": "warning"},
            {"name": "Queue", "value": 100, "formatted_value": "100%", "status": "ok"},
            {"name": "Storage", "value": 45.0, "formatted_value": "45.0%", "status": "critical"},
            {"name": "CDN", "value": 99.99, "formatted_value": "99.99%", "status": "ok"},
            {"name": "Search", "value": 92.3, "formatted_value": "92.3%", "status": "warning"},
            {"name": "Email", "value": 100, "formatted_value": "100%", "status": "ok"},
        ],
    },
    "table": {
        "panel_type": "table",
        "title": "Server Status",
        "timestamp": "2025-11-30 12:00 UTC",
        "columns": ["Host", "CPU", "Memory", "Status"],
        "rows": [
            ["web-server-01", "42%", "60%", "OK"],
            ["web-server-02", "35%", "45%", "OK"],
            ["db-primary", "78%", "82%", "Warning"],
            ["db-replica", "25%", "40%", "OK"],
            ["cache-01", "15%", "90%", "Critical"],
            ["worker-01", "55%", "50%", "OK"],
        ],
        "row_count": 6,
    },
    "timeseries": {
        "panel_type": "timeseries",
        "title": "CPU Usage",
        "timestamp": "2025-11-30 12:00 UTC",
        "series": [
            {
                "name": "cpu",
                "current": 42,
                "formatted_current": "42%",
                "min": 25,
                "max": 52,
                "avg": 40.29,
                "point_count": 7,
            }
        ],
        "chart_data": [
            {"time": "11:00", "value": 25, "label": "cpu"},
            {"time": "11:10", "value": 32, "label": "cpu"},
            {"time": "11:20", "value": 45, "label": "cpu"},
            {"time": "11:30", "value": 38, "label": "cpu"},
            {"time": "11:40", "value": 52, "label": "cpu"},
            {"time": "11:50", "value": 48, "label": "cpu"},
            {"time": "12:00", "value": 42, "label": "cpu"},
        ],
        "current_value": 42,
        "formatted_value": "42%",
        "min_value": 25,
        "max_value": 52,
        "avg_value": 40.29,
    },
}

# Panel type aliases
PANEL_ALIASES = {
    "graph": "timeseries",
    "barchart": "timeseries",
    "grafana-polystat-panel": "polystat",
}
