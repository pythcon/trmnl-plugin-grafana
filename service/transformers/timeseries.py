"""Transformer for Grafana time series panels."""

from datetime import datetime, timezone
from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer


@register_transformer("timeseries")
class TimeSeriesTransformer(BaseTransformer):
    """Transform time series panel data to TRMNL merge_variables."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform time series panel data.

        Produces:
            - chart_data: List of {time, value, label} for each series
            - series: List of series metadata
            - current_value: Most recent value
            - formatted_value: Formatted current value
            - min_value, max_value, avg_value: Statistics
        """
        variables = self._base_variables(panel)

        series_list = []
        all_chart_data = []

        for frame in query_result.frames:
            time_values = frame.get_time_values()
            value_fields = frame.get_value_fields()

            for field_name, values in value_fields:
                series_data = self._process_series(
                    field_name, time_values, values, panel
                )
                series_list.append(series_data["metadata"])
                all_chart_data.extend(series_data["points"])

        variables["series"] = series_list
        variables["chart_data"] = all_chart_data

        # Get current/last value from first series
        if series_list:
            first_series = series_list[0]
            variables["current_value"] = first_series.get("current")
            variables["formatted_value"] = first_series.get("formatted_current")
            variables["min_value"] = first_series.get("min")
            variables["max_value"] = first_series.get("max")
            variables["avg_value"] = first_series.get("avg")

        return variables

    def _process_series(
        self,
        name: str,
        time_values: list[Any],
        values: list[Any],
        panel: Panel,
    ) -> dict[str, Any]:
        """Process a single series of time series data."""
        unit = panel.get_unit()
        decimals = panel.get_decimals()

        # Filter out None values for statistics
        numeric_values = [v for v in values if isinstance(v, (int, float))]

        # Calculate statistics
        current = numeric_values[-1] if numeric_values else None
        min_val = min(numeric_values) if numeric_values else None
        max_val = max(numeric_values) if numeric_values else None
        avg_val = sum(numeric_values) / len(numeric_values) if numeric_values else None

        # Build chart data points
        points = []
        for i, (t, v) in enumerate(zip(time_values, values)):
            if v is not None:
                points.append({
                    "time": self._format_timestamp(t),
                    "value": v,
                    "label": name,
                })

        return {
            "metadata": {
                "name": name,
                "current": current,
                "formatted_current": self._format_value(current, unit, decimals),
                "min": min_val,
                "max": max_val,
                "avg": round(avg_val, 2) if avg_val is not None else None,
                "point_count": len(points),
            },
            "points": points,
        }

    def _format_timestamp(self, ts: Any) -> str:
        """Format a timestamp for display."""
        if ts is None:
            return ""

        try:
            # Grafana typically returns timestamps in milliseconds
            if isinstance(ts, (int, float)):
                if ts > 1_000_000_000_000:  # Milliseconds
                    ts = ts / 1000
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                return dt.strftime("%H:%M")
            return str(ts)
        except (ValueError, OSError):
            return str(ts)


@register_transformer("graph")
class GraphTransformer(TimeSeriesTransformer):
    """Transform legacy graph panel data (same as timeseries)."""
    pass


@register_transformer("barchart")
class BarChartTransformer(TimeSeriesTransformer):
    """Transform bar chart panel data (same structure as timeseries)."""
    pass
