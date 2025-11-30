"""Transformer for Grafana gauge panels."""

from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer


@register_transformer("gauge")
class GaugeTransformer(BaseTransformer):
    """Transform gauge panel data to TRMNL merge_variables."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform gauge panel data.

        Produces:
            - value: Raw numeric value
            - formatted_value: Value with unit formatting
            - percentage: Value as percentage of min-max range
            - color: Threshold-based color
            - min, max: Gauge range
        """
        variables = self._base_variables(panel)

        # Get the primary value
        value = query_result.get_single_value()
        variables["value"] = value

        # Get min/max from panel config
        min_val, max_val = panel.get_min_max()
        variables["min"] = min_val if min_val is not None else 0
        variables["max"] = max_val if max_val is not None else 100

        # Format with unit
        unit = panel.get_unit()
        decimals = panel.get_decimals()
        variables["formatted_value"] = self._format_value(value, unit, decimals)

        # Calculate percentage
        if isinstance(value, (int, float)):
            percentage = self._calculate_percentage(
                value, variables["min"], variables["max"]
            )
            variables["percentage"] = percentage
            variables["color"] = self._get_threshold_color(value, panel)
        else:
            variables["percentage"] = 0
            variables["color"] = "green"

        return variables

    def _calculate_percentage(
        self,
        value: float,
        min_val: float,
        max_val: float,
    ) -> int:
        """Calculate percentage of value within min-max range."""
        if max_val == min_val:
            return 100 if value >= max_val else 0

        percentage = ((value - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, int(round(percentage))))


@register_transformer("bargauge")
class BarGaugeTransformer(GaugeTransformer):
    """Transform bar gauge panel data (similar to gauge)."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform bar gauge panel data.

        Can have multiple values displayed as horizontal bars.
        """
        variables = self._base_variables(panel)

        # Get min/max from panel config
        min_val, max_val = panel.get_min_max()
        variables["min"] = min_val if min_val is not None else 0
        variables["max"] = max_val if max_val is not None else 100

        unit = panel.get_unit()
        decimals = panel.get_decimals()

        # Process all frames/values for multi-bar display
        bars = []
        for frame in query_result.frames:
            value_fields = frame.get_value_fields()
            for field_name, values in value_fields:
                # Get last value for each field
                value = values[-1] if values else None
                if value is not None and isinstance(value, (int, float)):
                    percentage = self._calculate_percentage(
                        value, variables["min"], variables["max"]
                    )
                    bars.append({
                        "name": field_name,
                        "value": value,
                        "formatted_value": self._format_value(value, unit, decimals),
                        "percentage": percentage,
                        "color": self._get_threshold_color(value, panel),
                    })

        variables["bars"] = bars

        # Also set primary value from first bar
        if bars:
            variables["value"] = bars[0]["value"]
            variables["formatted_value"] = bars[0]["formatted_value"]
            variables["percentage"] = bars[0]["percentage"]
            variables["color"] = bars[0]["color"]
        else:
            variables["value"] = None
            variables["formatted_value"] = "N/A"
            variables["percentage"] = 0
            variables["color"] = "green"

        return variables
