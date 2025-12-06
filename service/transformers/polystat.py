"""Transformer for Grafana polystat panels."""

from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer


@register_transformer("grafana-polystat-panel")
@register_transformer("polystat")
class PolystatTransformer(BaseTransformer):
    """Transform polystat panel data to TRMNL merge_variables."""

    def transform(
        self,
        panel: Panel,
        query_result: QueryResult,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Transform polystat panel data.

        Args:
            panel: Panel configuration
            query_result: Query results
            **kwargs: Additional options:
                - label_key: Prometheus label key for display names (default: "name")

        Produces:
            - stats: List of {name, value, status} for each hexagon
        """
        variables = self._base_variables(panel, kwargs.get("timezone", "UTC"))
        variables["panel_type"] = "polystat"

        label_key = kwargs.get("label_key", "name")
        stats = []

        for frame in query_result.frames:
            # Get the display name from labels using specified label key
            name = frame.get_display_name(label_key)

            # Get the value from value fields
            value = None
            value_fields = frame.get_value_fields()
            if value_fields:
                _field_name, values = value_fields[0]
                value = values[-1] if values else None

            status = self._get_status(value, panel)

            stats.append({
                "name": name,
                "value": value,
                "formatted_value": self._format_value(value, panel.get_unit(), panel.get_decimals()),
                "status": status,
            })

        variables["stats"] = stats
        return variables

    def _get_status_from_polystat_thresholds(self, value: float, thresholds: list) -> str:
        """Map value to status using polystat globalThresholdsConfig structure.

        Looks up by exact value match, then maps state to status:
        state 0 = ok, state 1 = warning, state 2 = critical
        """
        for threshold in thresholds:
            if threshold.get("value") == value:
                state = threshold.get("state", 0)
                if state == 2:
                    return "critical"
                elif state == 1:
                    return "warning"
                return "ok"
        return "ok"

    def _get_status(self, value: Any, panel: Panel) -> str:
        """
        Determine status based on value and thresholds.

        Returns: 'ok', 'warning', or 'critical'
        """
        if value is None:
            return "ok"

        if not isinstance(value, (int, float)):
            # For non-numeric values, check if it looks like an error/down state
            str_val = str(value).lower()
            if any(x in str_val for x in ["error", "down", "fail", "critical"]):
                return "critical"
            if any(x in str_val for x in ["warn", "degraded"]):
                return "warning"
            return "ok"

        # Check polystat global thresholds first
        global_thresholds = panel.options.get("globalThresholdsConfig", [])
        if global_thresholds:
            return self._get_status_from_polystat_thresholds(value, global_thresholds)

        # Fall back to standard thresholds
        thresholds = panel.get_thresholds()
        if not thresholds:
            # Fallback for service health metrics: 0 = down/critical
            if value == 0:
                return "critical"
            return "ok"

        # Find the applicable threshold
        color = "green"
        for step in thresholds:
            step_value = step.get("value")
            if step_value is None or value >= step_value:
                color = step.get("color", "green")

        # Map Grafana colors to status
        color_lower = color.lower() if color else ""
        if "red" in color_lower:
            return "critical"
        elif "yellow" in color_lower or "orange" in color_lower:
            return "warning"
        return "ok"
