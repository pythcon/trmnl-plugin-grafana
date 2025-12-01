"""Transformer for Grafana table panels."""

import logging
from typing import Any

from service.grafana.models import Panel, QueryResult
from service.transformers import register_transformer
from service.transformers.base import BaseTransformer

logger = logging.getLogger(__name__)


@register_transformer("table")
class TableTransformer(BaseTransformer):
    """Transform table panel data to TRMNL merge_variables."""

    def transform(self, panel: Panel, query_result: QueryResult, **kwargs: Any) -> dict[str, Any]:
        """
        Transform table panel data.

        Handles two formats:
        1. Single frame with multiple rows (standard table)
        2. Multiple frames with labels (Prometheus instant query)

        Applies panel transformations:
        - excludeByName: Hide specified columns
        - renameByName: Rename column headers

        Produces:
            - columns: List of column headers
            - rows: List of row data (list of cell values)
            - row_count: Total number of rows
        """
        variables = self._base_variables(panel)

        columns: list[str] = []
        rows: list[list[str]] = []

        if not query_result.frames:
            variables["columns"] = columns
            variables["rows"] = rows
            variables["row_count"] = 0
            return variables

        # Get transformations from panel
        excluded_fields = panel.get_excluded_fields()
        field_renames = panel.get_field_renames()

        # Check if this is a multi-frame Prometheus format
        # (multiple frames, each with labels on the value field)
        if len(query_result.frames) > 1 and self._is_prometheus_table_format(query_result):
            columns, rows = self._transform_prometheus_table(
                query_result, excluded_fields, field_renames, **kwargs
            )
        else:
            # Standard single-frame table format
            columns, rows = self._transform_standard_table(
                query_result, excluded_fields, field_renames
            )

        variables["columns"] = columns
        variables["rows"] = rows
        variables["row_count"] = len(rows)

        return variables

    def _is_prometheus_table_format(self, query_result: QueryResult) -> bool:
        """Check if this looks like a Prometheus instant query result."""
        if not query_result.frames:
            return False

        # Check first frame for labels on value fields
        frame = query_result.frames[0]
        for field in frame.fields:
            if field.get("type") != "time" and field.get("labels"):
                return True
        return False

    def _transform_prometheus_table(
        self,
        query_result: QueryResult,
        excluded_fields: set[str],
        field_renames: dict[str, str],
        **kwargs: Any,
    ) -> tuple[list[str], list[list[str]]]:
        """
        Transform Prometheus instant query format (multiple frames with labels).

        Each frame represents one time series with labels.
        Extracts label values to build table rows.
        """
        label_key = kwargs.get("label_key", "service_name")

        # Collect all unique label keys across all frames
        all_label_keys: set[str] = set()
        for frame in query_result.frames:
            for field in frame.fields:
                if field.get("type") != "time":
                    labels = field.get("labels", {})
                    all_label_keys.update(labels.keys())

        # Remove internal labels and excluded fields
        internal_labels = {"__name__"}
        label_keys = sorted(all_label_keys - internal_labels - excluded_fields)

        # Prioritize certain columns (if not excluded)
        priority_cols = ["service_name", "name", "instance", "job", "state"]
        ordered_keys = []
        for key in priority_cols:
            if key in label_keys:
                ordered_keys.append(key)
                label_keys.remove(key)
        ordered_keys.extend(label_keys)

        # Check if "Value" column is excluded
        include_value = "Value" not in excluded_fields and "value" not in excluded_fields

        # Build columns with renames applied
        columns: list[str] = []
        for key in ordered_keys:
            # Check for rename, otherwise format the column name
            if key in field_renames:
                columns.append(field_renames[key])
            else:
                columns.append(self._format_column_name(key))

        if include_value:
            value_col_name = field_renames.get("Value", field_renames.get("value", "Value"))
            columns.append(value_col_name)

        # Build rows from each frame
        rows: list[list[str]] = []
        for frame in query_result.frames:
            # Find the value field (non-time field)
            value_field = None
            value_idx = -1
            for i, field in enumerate(frame.fields):
                if field.get("type") != "time":
                    value_field = field
                    value_idx = i
                    break

            if value_field is None:
                continue

            labels = value_field.get("labels", {})

            # Get the value (last value in the array)
            value = ""
            if frame.values and value_idx < len(frame.values):
                values_arr = frame.values[value_idx]
                if values_arr:
                    value = self._format_cell(values_arr[-1])

            # Build row with label values
            row = [labels.get(key, "") for key in ordered_keys]
            if include_value:
                row.append(value)
            rows.append(row)

        # Sort by the label_key column if it exists
        if label_key in ordered_keys:
            sort_idx = ordered_keys.index(label_key)
            rows.sort(key=lambda r: r[sort_idx].lower() if r[sort_idx] else "")

        return columns, rows

    def _transform_standard_table(
        self,
        query_result: QueryResult,
        excluded_fields: set[str],
        field_renames: dict[str, str],
    ) -> tuple[list[str], list[list[str]]]:
        """Transform standard single-frame table format."""
        frame = query_result.frames[0]

        # Get column names from fields, filtering out excluded ones
        all_field_names = frame.get_field_names()

        # Build list of included column indices and names
        included_indices: list[int] = []
        columns: list[str] = []
        for idx, name in enumerate(all_field_names):
            if name not in excluded_fields:
                included_indices.append(idx)
                # Apply rename if exists
                display_name = field_renames.get(name, name)
                columns.append(display_name)

        # Transpose values to get rows (only for included columns)
        # Grafana returns columns of values, we need rows
        rows: list[list[str]] = []
        if frame.values:
            num_rows = len(frame.values[0]) if frame.values[0] else 0
            for row_idx in range(num_rows):
                row = []
                for col_idx in included_indices:
                    if col_idx < len(frame.values):
                        col_values = frame.values[col_idx]
                        if row_idx < len(col_values):
                            cell_value = col_values[row_idx]
                            row.append(self._format_cell(cell_value))
                        else:
                            row.append("")
                    else:
                        row.append("")
                rows.append(row)

        return columns, rows

    def _format_column_name(self, key: str) -> str:
        """Format a label key as a column name."""
        # Convert snake_case to Title Case
        return key.replace("_", " ").title()

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
