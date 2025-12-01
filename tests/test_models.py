"""Tests for Grafana data models."""

import pytest
from service.grafana.models import DataFrame, QueryResult, Panel, Dashboard


class TestDataFrame:
    """Tests for DataFrame model."""

    def test_from_api_response(self):
        """Test parsing DataFrame from API response."""
        frame_data = {
            "schema": {
                "name": "test_frame",
                "fields": [
                    {"name": "Time", "type": "time"},
                    {"name": "Value", "type": "number"},
                ],
            },
            "data": {
                "values": [
                    [1700000000000, 1700000060000],
                    [42.5, 45.2],
                ],
            },
        }

        frame = DataFrame.from_api_response(frame_data)

        assert frame.name == "test_frame"
        assert len(frame.fields) == 2
        assert frame.fields[0]["name"] == "Time"
        assert frame.fields[1]["name"] == "Value"
        assert len(frame.values) == 2
        assert frame.values[0] == [1700000000000, 1700000060000]
        assert frame.values[1] == [42.5, 45.2]

    def test_from_api_response_empty(self):
        """Test parsing empty API response."""
        frame = DataFrame.from_api_response({})

        assert frame.name == ""
        assert frame.fields == []
        assert frame.values == []

    def test_from_api_response_root_format(self):
        """Test parsing DataFrame from API response with root-level fields/values (table format)."""
        frame_data = {
            "name": "table_frame",
            "fields": [
                {"name": "Host", "type": "string"},
                {"name": "CPU", "type": "number"},
            ],
            "values": [
                ["server-1", "server-2"],
                [42, 35],
            ],
        }

        frame = DataFrame.from_api_response(frame_data)

        assert frame.name == "table_frame"
        assert len(frame.fields) == 2
        assert frame.fields[0]["name"] == "Host"
        assert frame.fields[1]["name"] == "CPU"
        assert len(frame.values) == 2
        assert frame.values[0] == ["server-1", "server-2"]
        assert frame.values[1] == [42, 35]

    def test_get_field_names(self, sample_dataframe: DataFrame):
        """Test getting field names."""
        names = sample_dataframe.get_field_names()
        assert names == ["Time", "Value"]

    def test_get_field_names_with_missing_name(self):
        """Test field names fallback for unnamed fields."""
        frame = DataFrame(
            name="test",
            fields=[{"type": "number"}, {"name": "Named"}],
            values=[[], []],
        )
        names = frame.get_field_names()
        assert names == ["field_0", "Named"]

    def test_get_field_by_name(self, sample_dataframe: DataFrame):
        """Test getting field by name."""
        field = sample_dataframe.get_field_by_name("Value")
        assert field is not None
        assert field["type"] == "number"

    def test_get_field_by_name_not_found(self, sample_dataframe: DataFrame):
        """Test getting non-existent field returns None."""
        assert sample_dataframe.get_field_by_name("NonExistent") is None

    def test_get_values_by_field_name(self, sample_dataframe: DataFrame):
        """Test getting values by field name."""
        values = sample_dataframe.get_values_by_field_name("Value")
        assert values == [42.5, 45.2, 43.1]

    def test_get_values_by_field_name_not_found(self, sample_dataframe: DataFrame):
        """Test getting values for non-existent field returns None."""
        assert sample_dataframe.get_values_by_field_name("NonExistent") is None

    def test_get_time_values(self, sample_dataframe: DataFrame):
        """Test getting time values."""
        times = sample_dataframe.get_time_values()
        assert times == [1700000000000, 1700000060000, 1700000120000]

    def test_get_time_values_fallback(self):
        """Test time values fallback to first field with large numbers."""
        frame = DataFrame(
            name="test",
            fields=[{"name": "ts", "type": "number"}],
            values=[[1700000000000, 1700000060000]],
        )
        times = frame.get_time_values()
        assert times == [1700000000000, 1700000060000]

    def test_get_time_values_empty(self):
        """Test getting time values from empty frame."""
        frame = DataFrame(name="test", fields=[], values=[])
        assert frame.get_time_values() == []

    def test_get_value_fields(self, sample_dataframe: DataFrame):
        """Test getting non-time value fields."""
        value_fields = sample_dataframe.get_value_fields()
        assert len(value_fields) == 1
        assert value_fields[0][0] == "Value"
        assert value_fields[0][1] == [42.5, 45.2, 43.1]


class TestQueryResult:
    """Tests for QueryResult model."""

    def test_from_api_response(self, grafana_query_response: dict):
        """Test parsing QueryResult from API response."""
        result = QueryResult.from_api_response(grafana_query_response)

        assert len(result.frames) == 1
        assert result.error is None
        assert result.frames[0].name == "cpu"

    def test_from_api_response_with_error(self):
        """Test parsing response with error."""
        response = {
            "results": {
                "A": {"error": "Query failed"},
            }
        }
        result = QueryResult.from_api_response(response)

        assert result.error == "Query failed"
        assert len(result.frames) == 0

    def test_from_api_response_empty(self):
        """Test parsing empty response."""
        result = QueryResult.from_api_response({})

        assert len(result.frames) == 0
        assert result.error is None

    def test_get_single_value(self, sample_stat_query_result: QueryResult):
        """Test getting single value for stat panels."""
        value = sample_stat_query_result.get_single_value()
        assert value == 85.5

    def test_get_single_value_from_timeseries(self, sample_query_result: QueryResult):
        """Test getting single value from timeseries returns last value."""
        value = sample_query_result.get_single_value()
        assert value == 43.1

    def test_get_single_value_empty(self):
        """Test getting single value from empty result."""
        result = QueryResult()
        assert result.get_single_value() is None


class TestPanel:
    """Tests for Panel model."""

    def test_from_api_response(self):
        """Test parsing Panel from API response."""
        panel_data = {
            "id": 1,
            "type": "stat",
            "title": "CPU Usage",
            "targets": [{"refId": "A", "expr": "cpu_usage"}],
            "options": {"colorMode": "background"},
            "fieldConfig": {
                "defaults": {
                    "unit": "percent",
                    "decimals": 1,
                }
            },
            "datasource": {"uid": "prometheus", "type": "prometheus"},
            "description": "Server CPU",
        }

        panel = Panel.from_api_response(panel_data)

        assert panel.id == 1
        assert panel.type == "stat"
        assert panel.title == "CPU Usage"
        assert len(panel.targets) == 1
        assert panel.datasource_uid == "prometheus"
        assert panel.description == "Server CPU"

    def test_from_api_response_minimal(self):
        """Test parsing minimal panel data."""
        panel = Panel.from_api_response({})

        assert panel.id == 0
        assert panel.type == "unknown"
        assert panel.title == "Untitled"
        assert panel.targets == []

    def test_datasource_uid_from_targets(self):
        """Test getting datasource UID from targets."""
        panel = Panel(
            id=1,
            type="stat",
            title="Test",
            targets=[{"refId": "A", "datasource": {"uid": "test-ds"}}],
        )
        assert panel.datasource_uid == "test-ds"

    def test_datasource_uid_none(self):
        """Test datasource_uid when not set."""
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        assert panel.datasource_uid is None

    def test_get_unit(self, sample_panel: Panel):
        """Test getting unit from field config."""
        assert sample_panel.get_unit() == "percent"

    def test_get_unit_empty(self):
        """Test getting unit when not configured."""
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        assert panel.get_unit() == ""

    def test_get_decimals(self, sample_panel: Panel):
        """Test getting decimals from field config."""
        assert sample_panel.get_decimals() == 1

    def test_get_decimals_none(self):
        """Test getting decimals when not configured."""
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        assert panel.get_decimals() is None

    def test_get_thresholds(self, sample_panel: Panel):
        """Test getting thresholds."""
        thresholds = sample_panel.get_thresholds()
        assert len(thresholds) == 3
        assert thresholds[1]["value"] == 70
        assert thresholds[1]["color"] == "yellow"

    def test_get_thresholds_empty(self):
        """Test getting thresholds when not configured."""
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        assert panel.get_thresholds() == []

    def test_get_min_max(self, sample_gauge_panel: Panel):
        """Test getting min/max values."""
        min_val, max_val = sample_gauge_panel.get_min_max()
        assert min_val == 0
        assert max_val == 100

    def test_get_min_max_none(self):
        """Test getting min/max when not configured."""
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        min_val, max_val = panel.get_min_max()
        assert min_val is None
        assert max_val is None


class TestDashboard:
    """Tests for Dashboard model."""

    def test_from_api_response(self, grafana_dashboard_response: dict):
        """Test parsing Dashboard from API response."""
        dashboard = Dashboard.from_api_response(grafana_dashboard_response)

        assert dashboard.uid == "abc123"
        assert dashboard.title == "Production Metrics"
        assert dashboard.tags == ["production", "monitoring"]
        # Should have 2 panels (1 regular + 1 nested in row)
        assert len(dashboard.panels) == 2

    def test_from_api_response_nested_panels(self, grafana_dashboard_response: dict):
        """Test that nested panels in rows are flattened."""
        dashboard = Dashboard.from_api_response(grafana_dashboard_response)

        panel_types = [p.type for p in dashboard.panels]
        assert "stat" in panel_types
        assert "timeseries" in panel_types
        assert "row" not in panel_types

    def test_from_api_response_empty(self):
        """Test parsing empty response."""
        dashboard = Dashboard.from_api_response({})

        assert dashboard.uid == ""
        assert dashboard.title == "Untitled"
        assert dashboard.panels == []
        assert dashboard.tags == []

    def test_get_panel_by_id(self, sample_dashboard: Dashboard):
        """Test finding panel by ID."""
        panel = sample_dashboard.get_panel_by_id(1)
        assert panel is not None
        assert panel.id == 1
        assert panel.title == "CPU Usage"

    def test_get_panel_by_id_not_found(self, sample_dashboard: Dashboard):
        """Test panel not found returns None."""
        assert sample_dashboard.get_panel_by_id(999) is None
