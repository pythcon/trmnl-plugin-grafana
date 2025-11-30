"""Tests to verify transformer output matches Liquid template expectations.

These tests ensure that the merge_variables produced by transformers contain
all the fields expected by the Liquid templates.
"""

import pytest
from service.grafana.models import Panel, DataFrame, QueryResult
from service.transformers import get_transformer
from service.transformers.stat import StatTransformer
from service.transformers.gauge import GaugeTransformer, BarGaugeTransformer
from service.transformers.timeseries import TimeSeriesTransformer
from service.transformers.table import TableTransformer


class TestStatTemplateVariables:
    """Test stat panel template variables."""

    def test_stat_has_required_variables(
        self,
        sample_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test stat transformer produces required template variables."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, sample_stat_query_result)

        # Required for all templates
        assert "panel_type" in result
        assert result["panel_type"] == "stat"
        assert "title" in result
        assert "timestamp" in result

        # Required for stat panel
        assert "value" in result
        assert "formatted_value" in result
        assert "color" in result

    def test_stat_value_types(
        self,
        sample_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test stat values have correct types."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, sample_stat_query_result)

        assert isinstance(result["panel_type"], str)
        assert isinstance(result["title"], str)
        assert isinstance(result["formatted_value"], str)
        assert isinstance(result["color"], str)
        # value can be numeric or None
        assert result["value"] is None or isinstance(result["value"], (int, float))


class TestGaugeTemplateVariables:
    """Test gauge panel template variables."""

    def test_gauge_has_required_variables(
        self,
        sample_gauge_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test gauge transformer produces required template variables."""
        transformer = GaugeTransformer()
        result = transformer.transform(sample_gauge_panel, sample_stat_query_result)

        # Required for gauge display
        assert "panel_type" in result
        assert result["panel_type"] == "gauge"
        assert "value" in result
        assert "formatted_value" in result
        assert "percentage" in result
        assert "min" in result
        assert "max" in result
        assert "color" in result
        assert "title" in result

    def test_gauge_percentage_in_range(
        self,
        sample_gauge_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test gauge percentage is 0-100."""
        transformer = GaugeTransformer()
        result = transformer.transform(sample_gauge_panel, sample_stat_query_result)

        assert isinstance(result["percentage"], int)
        assert 0 <= result["percentage"] <= 100

    def test_gauge_min_max_numeric(
        self,
        sample_gauge_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test gauge min/max are numeric."""
        transformer = GaugeTransformer()
        result = transformer.transform(sample_gauge_panel, sample_stat_query_result)

        assert isinstance(result["min"], (int, float))
        assert isinstance(result["max"], (int, float))


class TestBarGaugeTemplateVariables:
    """Test bar gauge panel template variables."""

    def test_bargauge_has_bars(self, sample_gauge_panel: Panel):
        """Test bar gauge produces bars array."""
        transformer = BarGaugeTransformer()

        frame = DataFrame(
            name="A",
            fields=[
                {"name": "Server1", "type": "number"},
                {"name": "Server2", "type": "number"},
            ],
            values=[[75.0], [50.0]],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_gauge_panel, query_result)

        assert "bars" in result
        assert isinstance(result["bars"], list)
        assert len(result["bars"]) == 2

    def test_bargauge_bar_structure(self, sample_gauge_panel: Panel):
        """Test each bar has required fields."""
        transformer = BarGaugeTransformer()

        frame = DataFrame(
            name="A",
            fields=[{"name": "Test", "type": "number"}],
            values=[[75.0]],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_gauge_panel, query_result)

        bar = result["bars"][0]
        assert "name" in bar
        assert "value" in bar
        assert "formatted_value" in bar
        assert "percentage" in bar
        assert "color" in bar


class TestTimeseriesTemplateVariables:
    """Test timeseries panel template variables."""

    def test_timeseries_has_chart_data(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test timeseries produces chart_data."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        assert "panel_type" in result
        assert result["panel_type"] == "timeseries"
        assert "chart_data" in result
        assert isinstance(result["chart_data"], list)

    def test_timeseries_chart_point_structure(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test chart data points have required fields."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        assert len(result["chart_data"]) > 0
        point = result["chart_data"][0]

        # Each point needs time, value, label for the templates
        assert "time" in point
        assert "value" in point
        assert "label" in point

    def test_timeseries_has_series_metadata(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test timeseries produces series metadata."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        assert "series" in result
        assert isinstance(result["series"], list)
        assert len(result["series"]) > 0

        series = result["series"][0]
        assert "name" in series
        assert "current" in series
        assert "min" in series
        assert "max" in series


class TestTableTemplateVariables:
    """Test table panel template variables."""

    def test_table_has_required_variables(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test table produces required variables."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        assert "panel_type" in result
        assert result["panel_type"] == "table"
        assert "columns" in result
        assert "rows" in result
        assert "row_count" in result

    def test_table_columns_are_strings(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test table columns are list of strings."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        assert isinstance(result["columns"], list)
        for col in result["columns"]:
            assert isinstance(col, str)

    def test_table_rows_are_nested_lists(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test table rows are list of lists."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        assert isinstance(result["rows"], list)
        for row in result["rows"]:
            assert isinstance(row, list)
            for cell in row:
                assert isinstance(cell, str)


class TestPolystatTemplateVariables:
    """Test polystat panel template variables structure."""

    def test_polystat_structure(self):
        """Test expected polystat variables structure.

        Note: There's no dedicated polystat transformer yet.
        This test documents the expected structure for the templates.
        """
        # Expected structure for polystat template variables
        expected_structure = {
            "panel_type": "polystat",
            "title": "Service Status",
            "stats": [
                {"name": "API", "status": "ok"},
                {"name": "DB", "status": "warning"},
                {"name": "Cache", "status": "critical"},
            ],
        }

        # Verify structure
        assert expected_structure["panel_type"] == "polystat"
        assert "stats" in expected_structure
        assert isinstance(expected_structure["stats"], list)

        for stat in expected_structure["stats"]:
            assert "name" in stat
            assert "status" in stat
            assert stat["status"] in ["ok", "warning", "critical"]


class TestErrorTemplateVariables:
    """Test error panel template variables."""

    def test_error_structure(self):
        """Test error panel variable structure."""
        error_variables = {
            "panel_type": "error",
            "title": "Error",
            "error_message": "Failed to connect to Grafana",
        }

        assert error_variables["panel_type"] == "error"
        assert "title" in error_variables
        assert "error_message" in error_variables


class TestGetTransformerIntegration:
    """Integration tests for transformer registry."""

    @pytest.mark.parametrize("panel_type,expected_keys", [
        ("stat", ["value", "formatted_value", "color"]),
        ("gauge", ["value", "formatted_value", "percentage", "min", "max"]),
        ("timeseries", ["chart_data", "series"]),
        ("table", ["columns", "rows", "row_count"]),
    ])
    def test_transformer_produces_expected_keys(
        self,
        panel_type: str,
        expected_keys: list[str],
    ):
        """Test each transformer type produces expected keys."""
        # Create a generic panel
        panel = Panel(
            id=1,
            type=panel_type,
            title="Test Panel",
            targets=[{"refId": "A"}],
            field_config={
                "defaults": {
                    "min": 0,
                    "max": 100,
                }
            },
        )

        # Create query result with sample data
        frame = DataFrame(
            name="A",
            fields=[
                {"name": "Time", "type": "time"},
                {"name": "Value", "type": "number"},
            ],
            values=[
                [1700000000000, 1700000060000],
                [42.5, 45.2],
            ],
        )
        query_result = QueryResult(frames=[frame])

        transformer = get_transformer(panel_type)
        result = transformer.transform(panel, query_result)

        # Common keys
        assert "panel_type" in result
        assert "title" in result

        # Type-specific keys
        for key in expected_keys:
            assert key in result, f"Missing expected key: {key} for panel_type: {panel_type}"
