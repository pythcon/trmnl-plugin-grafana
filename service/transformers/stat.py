"""Transformer for Grafana stat panels."""

from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer


@register_transformer("stat")
class StatTransformer(BaseTransformer):
    """Transform stat panel data to TRMNL merge_variables."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform stat panel data.

        Produces:
            - value: Raw numeric value
            - formatted_value: Value with unit formatting
            - color: Threshold-based color (green/yellow/red)
            - sparkline: Optional sparkline data points
        """
        variables = self._base_variables(panel)

        # Get the primary value
        value = query_result.get_single_value()
        variables["value"] = value

        # Format with unit
        unit = panel.get_unit()
        decimals = panel.get_decimals()
        variables["formatted_value"] = self._format_value(value, unit, decimals)

        # Determine color based on thresholds
        if isinstance(value, (int, float)):
            variables["color"] = self._get_threshold_color(value, panel)
        else:
            variables["color"] = "green"

        # Check for sparkline data (multiple values in frame)
        sparkline_data = self._extract_sparkline(query_result)
        if sparkline_data:
            variables["sparkline"] = sparkline_data

        return variables

    def _extract_sparkline(self, query_result: QueryResult) -> list[dict[str, Any]]:
        """Extract sparkline data points if available."""
        if not query_result.frames:
            return []

        frame = query_result.frames[0]
        time_values = frame.get_time_values()
        value_fields = frame.get_value_fields()

        if not value_fields or not time_values:
            return []

        _name, values = value_fields[0]
        if len(values) <= 1:
            return []

        # Return list of {time, value} for sparkline
        return [
            {"time": t, "value": v}
            for t, v in zip(time_values, values)
            if v is not None
        ]
