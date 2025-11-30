"""Transformer for Grafana table panels."""

from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer


@register_transformer("table")
class TableTransformer(BaseTransformer):
    """Transform table panel data to TRMNL merge_variables."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform table panel data.

        Produces:
            - columns: List of column headers
            - rows: List of row data (list of cell values)
            - row_count: Total number of rows
        """
        variables = self._base_variables(panel)

        columns = []
        rows = []

        if query_result.frames:
            frame = query_result.frames[0]

            # Get column names from fields
            columns = frame.get_field_names()

            # Transpose values to get rows
            # Grafana returns columns of values, we need rows
            if frame.values:
                num_rows = len(frame.values[0]) if frame.values[0] else 0
                for row_idx in range(num_rows):
                    row = []
                    for col_idx, col_values in enumerate(frame.values):
                        if row_idx < len(col_values):
                            cell_value = col_values[row_idx]
                            row.append(self._format_cell(cell_value))
                        else:
                            row.append("")
                    rows.append(row)

        variables["columns"] = columns
        variables["rows"] = rows
        variables["row_count"] = len(rows)

        return variables

    def _format_cell(self, value: Any) -> str:
        """Format a cell value for display."""
        if value is None:
            return ""

        if isinstance(value, float):
            # Format floats reasonably
            if value == int(value):
                return str(int(value))
            return f"{value:.2f}"

        if isinstance(value, bool):
            return "Yes" if value else "No"

        return str(value)


@register_transformer("table-old")
class TableOldTransformer(TableTransformer):
    """Transform legacy table panel data (same as table)."""
    pass
