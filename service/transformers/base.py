"""Base transformer for converting Grafana data to TRMNL merge_variables."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from service.grafana.models import Panel, QueryResult


class BaseTransformer(ABC):
    """
    Base class for panel type transformers.

    Each transformer converts Grafana query results into the merge_variables
    format expected by TRMNL Liquid templates.
    """

    panel_type: str = ""

    @abstractmethod
    def transform(
        self,
        panel: Panel,
        query_result: QueryResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Transform Grafana data to TRMNL merge_variables.

        Args:
            panel: Panel configuration from Grafana
            query_result: Query result data from Grafana
            **kwargs: Additional options (e.g., label_key for polystat)

        Returns:
            Dictionary of merge_variables for TRMNL templates
        """
        pass

    def _base_variables(self, panel: Panel) -> dict[str, Any]:
        """
        Common variables for all panel types.

        Args:
            panel: Panel configuration

        Returns:
            Base merge_variables dict
        """
        return {
            "panel_type": self.panel_type,
            "title": panel.title,
            "description": panel.description,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "unit": panel.get_unit(),
        }

    def _format_value(
        self,
        value: Any,
        unit: str = "",
        decimals: int | None = None,
    ) -> str:
        """
        Format a value with unit and decimal places.

        Args:
            value: Raw value
            unit: Unit suffix (e.g., "%", "ms")
            decimals: Number of decimal places (None = auto)

        Returns:
            Formatted string
        """
        if value is None:
            return "N/A"

        if isinstance(value, float):
            if decimals is not None:
                value = round(value, decimals)
            elif value == int(value):
                value = int(value)
            else:
                value = round(value, 2)

        if unit:
            # Handle common unit symbols
            unit_map = {
                "percent": "%",
                "percentunit": "%",
                "bytes": " B",
                "decbytes": " B",
                "bits": " b",
                "s": "s",
                "ms": "ms",
                "ns": "ns",
            }
            unit_suffix = unit_map.get(unit, f" {unit}" if unit else "")
            return f"{value}{unit_suffix}"

        return str(value)

    def _get_color_name(self, color: str | None) -> str:
        """
        Convert Grafana color to a simple color name.

        Args:
            color: Grafana color name or hex

        Returns:
            Simple color name (green, yellow, red, etc.)
        """
        if not color:
            return "green"

        color_lower = color.lower()
        if "green" in color_lower:
            return "green"
        elif "yellow" in color_lower or "orange" in color_lower:
            return "yellow"
        elif "red" in color_lower:
            return "red"
        elif "blue" in color_lower:
            return "blue"
        else:
            return "green"

    def _get_threshold_color(
        self,
        value: float | None,
        panel: Panel,
    ) -> str:
        """
        Get threshold color for a value.

        Args:
            value: The value to check
            panel: Panel with threshold configuration

        Returns:
            Color name based on thresholds
        """
        if value is None:
            return "green"

        thresholds = panel.get_thresholds()
        if not thresholds:
            return "green"

        color = "green"
        for step in thresholds:
            step_value = step.get("value")
            if step_value is None or value >= step_value:
                color = self._get_color_name(step.get("color"))

        return color
