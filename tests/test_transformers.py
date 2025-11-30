"""Tests for panel data transformers."""

import pytest
from service.grafana.models import Panel, DataFrame, QueryResult
from service.transformers import get_transformer, get_supported_types
from service.transformers.base import BaseTransformer
from service.transformers.stat import StatTransformer
from service.transformers.gauge import GaugeTransformer, BarGaugeTransformer
from service.transformers.timeseries import TimeSeriesTransformer
from service.transformers.table import TableTransformer


class TestTransformerRegistry:
    """Tests for transformer registry."""

    def test_get_supported_types(self):
        """Test getting list of supported panel types."""
        types = get_supported_types()
        assert "stat" in types
        assert "gauge" in types
        assert "timeseries" in types
        assert "table" in types
        assert "bargauge" in types

    def test_get_transformer_stat(self):
        """Test getting stat transformer."""
        transformer = get_transformer("stat")
        assert isinstance(transformer, StatTransformer)

    def test_get_transformer_gauge(self):
        """Test getting gauge transformer."""
        transformer = get_transformer("gauge")
        assert isinstance(transformer, GaugeTransformer)

    def test_get_transformer_timeseries(self):
        """Test getting timeseries transformer."""
        transformer = get_transformer("timeseries")
        assert isinstance(transformer, TimeSeriesTransformer)

    def test_get_transformer_table(self):
        """Test getting table transformer."""
        transformer = get_transformer("table")
        assert isinstance(transformer, TableTransformer)

    def test_get_transformer_unknown_falls_back_to_stat(self):
        """Test that unknown panel types fall back to StatTransformer."""
        transformer = get_transformer("unknown_panel_type")
        assert isinstance(transformer, StatTransformer)


class TestBaseTransformer:
    """Tests for BaseTransformer helper methods."""

    def test_format_value_with_percent_unit(self):
        """Test formatting value with percent unit."""
        transformer = StatTransformer()
        result = transformer._format_value(85.5, "percent", 1)
        assert result == "85.5%"

    def test_format_value_with_decimals(self):
        """Test formatting value with specific decimals."""
        transformer = StatTransformer()
        result = transformer._format_value(85.567, "", 2)
        assert result == "85.57"

    def test_format_value_auto_decimals(self):
        """Test formatting value with auto decimals."""
        transformer = StatTransformer()
        # Integer value
        assert transformer._format_value(85.0, "", None) == "85"
        # Float value
        assert transformer._format_value(85.567, "", None) == "85.57"

    def test_format_value_none(self):
        """Test formatting None value."""
        transformer = StatTransformer()
        assert transformer._format_value(None, "", None) == "N/A"

    def test_format_value_units(self):
        """Test formatting with various units."""
        transformer = StatTransformer()
        assert transformer._format_value(100, "bytes", None) == "100 B"
        assert transformer._format_value(50, "ms", None) == "50ms"
        assert transformer._format_value(25, "s", None) == "25s"

    def test_get_color_name(self):
        """Test color name normalization."""
        transformer = StatTransformer()
        assert transformer._get_color_name("green") == "green"
        assert transformer._get_color_name("dark-green") == "green"
        assert transformer._get_color_name("yellow") == "yellow"
        assert transformer._get_color_name("orange") == "yellow"
        assert transformer._get_color_name("red") == "red"
        assert transformer._get_color_name("blue") == "blue"
        assert transformer._get_color_name(None) == "green"
        assert transformer._get_color_name("unknown") == "green"

    def test_get_threshold_color(self, sample_panel: Panel):
        """Test threshold color determination."""
        transformer = StatTransformer()
        # Below all thresholds
        assert transformer._get_threshold_color(50, sample_panel) == "green"
        # Above yellow threshold
        assert transformer._get_threshold_color(75, sample_panel) == "yellow"
        # Above red threshold
        assert transformer._get_threshold_color(95, sample_panel) == "red"

    def test_get_threshold_color_no_thresholds(self):
        """Test threshold color with no thresholds configured."""
        transformer = StatTransformer()
        panel = Panel(id=1, type="stat", title="Test", targets=[])
        assert transformer._get_threshold_color(100, panel) == "green"

    def test_get_threshold_color_none_value(self, sample_panel: Panel):
        """Test threshold color with None value."""
        transformer = StatTransformer()
        assert transformer._get_threshold_color(None, sample_panel) == "green"


class TestStatTransformer:
    """Tests for StatTransformer."""

    def test_transform_basic(
        self,
        sample_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test basic stat transformation."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, sample_stat_query_result)

        assert result["panel_type"] == "stat"
        assert result["title"] == "CPU Usage"
        assert result["value"] == 85.5
        assert result["formatted_value"] == "85.5%"
        assert result["color"] == "yellow"  # 85.5 > 70 threshold
        assert "timestamp" in result

    def test_transform_with_sparkline(
        self,
        sample_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test stat transformation with sparkline data."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, sample_query_result)

        assert "sparkline" in result
        assert len(result["sparkline"]) == 3
        assert result["sparkline"][0]["value"] == 42.5

    def test_transform_no_sparkline_single_value(
        self,
        sample_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test stat transformation with single value has no sparkline."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, sample_stat_query_result)

        # Single value should not produce meaningful sparkline
        sparkline = result.get("sparkline", [])
        assert sparkline == [] or len(sparkline) <= 1

    def test_transform_empty_result(self, sample_panel: Panel):
        """Test stat transformation with empty query result."""
        transformer = StatTransformer()
        result = transformer.transform(sample_panel, QueryResult())

        assert result["value"] is None
        assert result["formatted_value"] == "N/A"
        assert result["color"] == "green"


class TestGaugeTransformer:
    """Tests for GaugeTransformer."""

    def test_transform_basic(
        self,
        sample_gauge_panel: Panel,
        sample_stat_query_result: QueryResult,
    ):
        """Test basic gauge transformation."""
        transformer = GaugeTransformer()
        result = transformer.transform(sample_gauge_panel, sample_stat_query_result)

        assert result["panel_type"] == "gauge"
        assert result["title"] == "Memory Usage"
        assert result["value"] == 85.5
        assert result["min"] == 0
        assert result["max"] == 100
        assert result["percentage"] == 86  # round(85.5)

    def test_transform_percentage_calculation(self, sample_gauge_panel: Panel):
        """Test percentage calculation for different values."""
        transformer = GaugeTransformer()

        # Create query result with specific value
        frame = DataFrame(
            name="A",
            fields=[{"name": "Value", "type": "number"}],
            values=[[50.0]],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_gauge_panel, query_result)
        assert result["percentage"] == 50

    def test_transform_percentage_clamp(self, sample_gauge_panel: Panel):
        """Test percentage is clamped to 0-100."""
        transformer = GaugeTransformer()

        # Value above max
        frame = DataFrame(
            name="A",
            fields=[{"name": "Value", "type": "number"}],
            values=[[150.0]],
        )
        query_result = QueryResult(frames=[frame])
        result = transformer.transform(sample_gauge_panel, query_result)
        assert result["percentage"] == 100

        # Value below min
        frame = DataFrame(
            name="A",
            fields=[{"name": "Value", "type": "number"}],
            values=[[-10.0]],
        )
        query_result = QueryResult(frames=[frame])
        result = transformer.transform(sample_gauge_panel, query_result)
        assert result["percentage"] == 0

    def test_transform_default_min_max(self, sample_panel: Panel):
        """Test default min/max when not configured."""
        transformer = GaugeTransformer()
        frame = DataFrame(
            name="A",
            fields=[{"name": "Value", "type": "number"}],
            values=[[50.0]],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_panel, query_result)
        assert result["min"] == 0
        assert result["max"] == 100


class TestBarGaugeTransformer:
    """Tests for BarGaugeTransformer."""

    def test_transform_multiple_values(self, sample_gauge_panel: Panel):
        """Test bar gauge with multiple values."""
        transformer = BarGaugeTransformer()

        # Create query result with multiple fields
        frame = DataFrame(
            name="A",
            fields=[
                {"name": "CPU", "type": "number"},
                {"name": "Memory", "type": "number"},
                {"name": "Disk", "type": "number"},
            ],
            values=[
                [75.0],
                [60.0],
                [45.0],
            ],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_gauge_panel, query_result)

        assert "bars" in result
        assert len(result["bars"]) == 3
        assert result["bars"][0]["name"] == "CPU"
        assert result["bars"][0]["value"] == 75.0
        assert result["bars"][0]["percentage"] == 75

    def test_transform_primary_value_from_first_bar(self, sample_gauge_panel: Panel):
        """Test that primary value comes from first bar."""
        transformer = BarGaugeTransformer()

        frame = DataFrame(
            name="A",
            fields=[{"name": "Test", "type": "number"}],
            values=[[42.0]],
        )
        query_result = QueryResult(frames=[frame])

        result = transformer.transform(sample_gauge_panel, query_result)

        assert result["value"] == 42.0
        assert result["formatted_value"] == "42%"

    def test_transform_empty_bars(self, sample_gauge_panel: Panel):
        """Test bar gauge with no values."""
        transformer = BarGaugeTransformer()
        result = transformer.transform(sample_gauge_panel, QueryResult())

        assert result["bars"] == []
        assert result["value"] is None
        assert result["formatted_value"] == "N/A"


class TestTimeSeriesTransformer:
    """Tests for TimeSeriesTransformer."""

    def test_transform_basic(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test basic timeseries transformation."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        assert result["panel_type"] == "timeseries"
        assert result["title"] == "Request Rate"
        assert "chart_data" in result
        assert "series" in result

    def test_transform_chart_data(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test chart data point structure."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        chart_data = result["chart_data"]
        assert len(chart_data) == 3
        assert "time" in chart_data[0]
        assert "value" in chart_data[0]
        assert "label" in chart_data[0]

    def test_transform_series_statistics(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test series statistics calculation."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        series = result["series"][0]
        assert series["current"] == 43.1  # Last value
        assert series["min"] == 42.5
        assert series["max"] == 45.2
        assert series["avg"] == pytest.approx(43.6, 0.1)

    def test_transform_current_value(
        self,
        sample_timeseries_panel: Panel,
        sample_query_result: QueryResult,
    ):
        """Test current value extraction."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, sample_query_result)

        assert result["current_value"] == 43.1

    def test_transform_empty_result(self, sample_timeseries_panel: Panel):
        """Test timeseries transformation with empty result."""
        transformer = TimeSeriesTransformer()
        result = transformer.transform(sample_timeseries_panel, QueryResult())

        assert result["chart_data"] == []
        assert result["series"] == []

    def test_format_timestamp_milliseconds(self):
        """Test timestamp formatting for milliseconds."""
        transformer = TimeSeriesTransformer()
        # Milliseconds timestamp
        result = transformer._format_timestamp(1700000000000)
        assert ":" in result  # Should be HH:MM format

    def test_format_timestamp_seconds(self):
        """Test timestamp formatting for seconds."""
        transformer = TimeSeriesTransformer()
        # Seconds timestamp
        result = transformer._format_timestamp(1700000000)
        assert ":" in result

    def test_format_timestamp_none(self):
        """Test timestamp formatting for None."""
        transformer = TimeSeriesTransformer()
        assert transformer._format_timestamp(None) == ""


class TestTableTransformer:
    """Tests for TableTransformer."""

    def test_transform_basic(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test basic table transformation."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        assert result["panel_type"] == "table"
        assert result["title"] == "Server Status"
        assert "columns" in result
        assert "rows" in result
        assert "row_count" in result

    def test_transform_columns(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test column extraction."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        columns = result["columns"]
        assert columns == ["Host", "CPU", "Memory", "Status"]

    def test_transform_rows(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test row data transposition."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        rows = result["rows"]
        assert len(rows) == 3
        assert rows[0] == ["server-1", "42", "60", "OK"]
        assert rows[1] == ["server-2", "35", "45", "OK"]
        assert rows[2] == ["server-3", "78", "82", "Warning"]

    def test_transform_row_count(
        self,
        sample_table_panel: Panel,
        sample_table_query_result: QueryResult,
    ):
        """Test row count."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, sample_table_query_result)

        assert result["row_count"] == 3

    def test_transform_empty_result(self, sample_table_panel: Panel):
        """Test table transformation with empty result."""
        transformer = TableTransformer()
        result = transformer.transform(sample_table_panel, QueryResult())

        assert result["columns"] == []
        assert result["rows"] == []
        assert result["row_count"] == 0

    def test_format_cell_float(self):
        """Test cell formatting for floats."""
        transformer = TableTransformer()
        assert transformer._format_cell(42.0) == "42"
        assert transformer._format_cell(42.567) == "42.57"

    def test_format_cell_bool(self):
        """Test cell formatting for booleans."""
        transformer = TableTransformer()
        assert transformer._format_cell(True) == "Yes"
        assert transformer._format_cell(False) == "No"

    def test_format_cell_none(self):
        """Test cell formatting for None."""
        transformer = TableTransformer()
        assert transformer._format_cell(None) == ""
