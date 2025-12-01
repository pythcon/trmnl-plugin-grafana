"""Data models for Grafana API responses."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataFrame:
    """Represents a Grafana data frame from query results."""

    name: str
    fields: list[dict[str, Any]]
    values: list[list[Any]]

    @classmethod
    def from_api_response(cls, frame_data: dict[str, Any]) -> "DataFrame":
        """Parse a data frame from Grafana API response.

        Handles two formats:
        - Nested: schema.fields, data.values (timeseries)
        - Root: fields, values directly on frame (table)
        """
        schema = frame_data.get("schema", {})
        data = frame_data.get("data", {})

        # Get fields - try schema first, then root level
        fields = schema.get("fields") or frame_data.get("fields", [])

        # Get values - try data first, then root level
        values = data.get("values") or frame_data.get("values", [])

        # Get name - try schema first, then root level
        name = schema.get("name") or frame_data.get("name", "")

        return cls(name=name, fields=fields, values=values)

    def get_field_names(self) -> list[str]:
        """Get list of field names."""
        return [f.get("name", f"field_{i}") for i, f in enumerate(self.fields)]

    def get_field_by_name(self, name: str) -> dict[str, Any] | None:
        """Get field configuration by name."""
        for f in self.fields:
            if f.get("name") == name:
                return f
        return None

    def get_values_by_field_name(self, name: str) -> list[Any] | None:
        """Get values for a specific field by name."""
        for i, f in enumerate(self.fields):
            if f.get("name") == name and i < len(self.values):
                return self.values[i]
        return None

    def get_time_values(self) -> list[Any]:
        """Get time/timestamp values (field with type='time' or common time names)."""
        # First, look for field with type="time"
        for i, f in enumerate(self.fields):
            if f.get("type") == "time" and i < len(self.values):
                return self.values[i]
        # Fallback to name-based detection
        for name in ["Time", "time", "timestamp", "Timestamp"]:
            values = self.get_values_by_field_name(name)
            if values is not None:
                return values
        # Final fallback to first field if it looks like timestamps
        if self.values and self.values[0]:
            first_val = self.values[0][0] if self.values[0] else None
            if isinstance(first_val, (int, float)) and first_val > 1_000_000_000:
                return self.values[0]
        return []

    def get_value_fields(self) -> list[tuple[str, list[Any]]]:
        """Get all non-time value fields with their names and values."""
        time_names = {"Time", "time", "timestamp", "Timestamp"}
        result = []
        for i, f in enumerate(self.fields):
            # Skip time fields by type or name
            if f.get("type") == "time":
                continue
            name = f.get("name", f"field_{i}")
            if name not in time_names and i < len(self.values):
                result.append((name, self.values[i]))
        return result

    def get_display_name(self, label_key: str = "name") -> str:
        """
        Get display name from field labels using specified label key.

        Args:
            label_key: The Prometheus label key to use (e.g., "service_name", "job")

        Returns:
            The label value, or frame name, or "Unknown"
        """
        # Look at non-time fields for labels
        time_names = {"Time", "time", "timestamp", "Timestamp"}

        for field in self.fields:
            field_name = field.get("name", "")
            if field_name in time_names:
                continue

            # Check for labels (Prometheus-style)
            labels = field.get("labels", {})
            if labels and label_key in labels:
                return labels[label_key]

        # Fall back to frame name if not a refId
        if self.name and self.name not in ("A", "B", "C", "D", "E"):
            return self.name

        return "Unknown"


@dataclass
class QueryResult:
    """Represents the result of a Grafana datasource query."""

    frames: list[DataFrame] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "QueryResult":
        """Parse query result from Grafana /api/ds/query response."""
        frames: list[DataFrame] = []
        error: str | None = None

        results = response.get("results", {})

        for ref_id, result in results.items():
            if "error" in result:
                error = result["error"]
                continue

            for frame_data in result.get("frames", []):
                frame = DataFrame.from_api_response(frame_data)
                # Set frame name from refId if not set
                if not frame.name:
                    frame.name = ref_id
                frames.append(frame)

        return cls(frames=frames, error=error)

    def get_single_value(self) -> Any | None:
        """Get a single value (for stat panels)."""
        if not self.frames:
            return None

        frame = self.frames[0]
        value_fields = frame.get_value_fields()
        if value_fields:
            _name, values = value_fields[0]
            if values:
                return values[-1]  # Return last value
        return None


@dataclass
class Panel:
    """Represents a Grafana dashboard panel."""

    id: int
    type: str
    title: str
    targets: list[dict[str, Any]]
    options: dict[str, Any] = field(default_factory=dict)
    field_config: dict[str, Any] = field(default_factory=dict)
    datasource: dict[str, Any] | None = None
    description: str = ""
    transformations: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, panel_data: dict[str, Any]) -> "Panel":
        """Parse panel from dashboard JSON."""
        return cls(
            id=panel_data.get("id", 0),
            type=panel_data.get("type", "unknown"),
            title=panel_data.get("title", "Untitled"),
            targets=panel_data.get("targets", []),
            options=panel_data.get("options", {}),
            field_config=panel_data.get("fieldConfig", {}),
            datasource=panel_data.get("datasource"),
            description=panel_data.get("description", ""),
            transformations=panel_data.get("transformations", []),
        )

    @property
    def datasource_uid(self) -> str | None:
        """Get the datasource UID for this panel."""
        if self.datasource:
            return self.datasource.get("uid")
        # Check targets for datasource
        for target in self.targets:
            ds = target.get("datasource", {})
            if isinstance(ds, dict) and ds.get("uid"):
                return ds["uid"]
        return None

    def get_unit(self) -> str:
        """Get the display unit from field config."""
        defaults = self.field_config.get("defaults", {})
        return defaults.get("unit", "")

    def get_decimals(self) -> int | None:
        """Get the decimal places from field config."""
        defaults = self.field_config.get("defaults", {})
        return defaults.get("decimals")

    def get_thresholds(self) -> list[dict[str, Any]]:
        """Get threshold configuration."""
        defaults = self.field_config.get("defaults", {})
        thresholds = defaults.get("thresholds", {})
        return thresholds.get("steps", [])

    def get_min_max(self) -> tuple[float | None, float | None]:
        """Get min/max values from field config."""
        defaults = self.field_config.get("defaults", {})
        return defaults.get("min"), defaults.get("max")

    def get_excluded_fields(self) -> set[str]:
        """Get field names that should be hidden based on 'organize' transformation."""
        excluded: set[str] = set()
        for t in self.transformations:
            if t.get("id") == "organize":
                options = t.get("options", {})
                for name, is_excluded in options.get("excludeByName", {}).items():
                    if is_excluded:
                        excluded.add(name)
        return excluded

    def get_field_renames(self) -> dict[str, str]:
        """Get field rename mappings from 'organize' transformation."""
        renames: dict[str, str] = {}
        for t in self.transformations:
            if t.get("id") == "organize":
                options = t.get("options", {})
                renames.update(options.get("renameByName", {}))
        return renames


@dataclass
class Dashboard:
    """Represents a Grafana dashboard."""

    uid: str
    title: str
    panels: list[Panel]
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> "Dashboard":
        """Parse dashboard from Grafana API response."""
        dashboard_data = response.get("dashboard", {})

        # Parse panels (handle nested panels in rows)
        panels: list[Panel] = []
        for panel_data in dashboard_data.get("panels", []):
            # Check for collapsed row with nested panels
            if panel_data.get("type") == "row" and "panels" in panel_data:
                for nested in panel_data["panels"]:
                    panels.append(Panel.from_api_response(nested))
            else:
                panels.append(Panel.from_api_response(panel_data))

        return cls(
            uid=dashboard_data.get("uid", ""),
            title=dashboard_data.get("title", "Untitled"),
            panels=panels,
            tags=dashboard_data.get("tags", []),
        )

    def get_panel_by_id(self, panel_id: int) -> Panel | None:
        """Find a panel by ID."""
        for panel in self.panels:
            if panel.id == panel_id:
                return panel
        return None
