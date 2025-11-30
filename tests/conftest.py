"""Pytest fixtures for TRMNL Grafana plugin tests."""

import pytest
from service.grafana.models import Panel, DataFrame, QueryResult, Dashboard


@pytest.fixture
def sample_panel() -> Panel:
    """Create a sample stat panel."""
    return Panel(
        id=1,
        type="stat",
        title="CPU Usage",
        targets=[{"refId": "A", "expr": "cpu_usage"}],
        options={},
        field_config={
            "defaults": {
                "unit": "percent",
                "decimals": 1,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 70},
                        {"color": "red", "value": 90},
                    ]
                }
            }
        },
        description="Server CPU utilization",
    )


@pytest.fixture
def sample_gauge_panel() -> Panel:
    """Create a sample gauge panel."""
    return Panel(
        id=2,
        type="gauge",
        title="Memory Usage",
        targets=[{"refId": "A", "expr": "memory_usage"}],
        options={},
        field_config={
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 60},
                        {"color": "red", "value": 80},
                    ]
                }
            }
        },
    )


@pytest.fixture
def sample_timeseries_panel() -> Panel:
    """Create a sample timeseries panel."""
    return Panel(
        id=3,
        type="timeseries",
        title="Request Rate",
        targets=[{"refId": "A", "expr": "rate(requests_total[5m])"}],
        options={},
        field_config={
            "defaults": {
                "unit": "reqps",
            }
        },
    )


@pytest.fixture
def sample_table_panel() -> Panel:
    """Create a sample table panel."""
    return Panel(
        id=4,
        type="table",
        title="Server Status",
        targets=[{"refId": "A"}],
        options={},
        field_config={},
    )


@pytest.fixture
def sample_dataframe() -> DataFrame:
    """Create a sample data frame with time series data."""
    return DataFrame(
        name="A",
        fields=[
            {"name": "Time", "type": "time"},
            {"name": "Value", "type": "number"},
        ],
        values=[
            [1700000000000, 1700000060000, 1700000120000],  # timestamps
            [42.5, 45.2, 43.1],  # values
        ],
    )


@pytest.fixture
def sample_stat_dataframe() -> DataFrame:
    """Create a data frame for stat panel (single value)."""
    return DataFrame(
        name="A",
        fields=[
            {"name": "Value", "type": "number"},
        ],
        values=[
            [85.5],
        ],
    )


@pytest.fixture
def sample_table_dataframe() -> DataFrame:
    """Create a data frame for table panel."""
    return DataFrame(
        name="A",
        fields=[
            {"name": "Host", "type": "string"},
            {"name": "CPU", "type": "number"},
            {"name": "Memory", "type": "number"},
            {"name": "Status", "type": "string"},
        ],
        values=[
            ["server-1", "server-2", "server-3"],
            [42, 35, 78],
            [60, 45, 82],
            ["OK", "OK", "Warning"],
        ],
    )


@pytest.fixture
def sample_query_result(sample_dataframe: DataFrame) -> QueryResult:
    """Create a sample query result."""
    return QueryResult(frames=[sample_dataframe])


@pytest.fixture
def sample_stat_query_result(sample_stat_dataframe: DataFrame) -> QueryResult:
    """Create a query result for stat panel."""
    return QueryResult(frames=[sample_stat_dataframe])


@pytest.fixture
def sample_table_query_result(sample_table_dataframe: DataFrame) -> QueryResult:
    """Create a query result for table panel."""
    return QueryResult(frames=[sample_table_dataframe])


@pytest.fixture
def sample_dashboard(sample_panel: Panel) -> Dashboard:
    """Create a sample dashboard."""
    return Dashboard(
        uid="test-dashboard",
        title="Test Dashboard",
        panels=[sample_panel],
        tags=["test"],
    )


@pytest.fixture
def grafana_dashboard_response() -> dict:
    """Sample Grafana API dashboard response."""
    return {
        "dashboard": {
            "uid": "abc123",
            "title": "Production Metrics",
            "tags": ["production", "monitoring"],
            "panels": [
                {
                    "id": 1,
                    "type": "stat",
                    "title": "CPU Usage",
                    "targets": [{"refId": "A", "expr": "cpu_usage"}],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                        }
                    },
                },
                {
                    "id": 2,
                    "type": "row",
                    "title": "Details",
                    "panels": [
                        {
                            "id": 3,
                            "type": "timeseries",
                            "title": "Traffic",
                            "targets": [{"refId": "A"}],
                        }
                    ],
                },
            ],
        }
    }


@pytest.fixture
def grafana_query_response() -> dict:
    """Sample Grafana API query response."""
    return {
        "results": {
            "A": {
                "frames": [
                    {
                        "schema": {
                            "name": "cpu",
                            "fields": [
                                {"name": "Time", "type": "time"},
                                {"name": "Value", "type": "number"},
                            ],
                        },
                        "data": {
                            "values": [
                                [1700000000000, 1700000060000],
                                [42.5, 45.2],
                            ]
                        },
                    }
                ]
            }
        }
    }
