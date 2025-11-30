"""Data transformers for converting Grafana data to TRMNL merge_variables."""

from pathlib import Path
import importlib

from .base import BaseTransformer

# Registry of transformers
_TRANSFORMERS: dict[str, type[BaseTransformer]] = {}


def register_transformer(panel_type: str):
    """Decorator to register a transformer for a panel type."""
    def decorator(cls: type[BaseTransformer]) -> type[BaseTransformer]:
        cls.panel_type = panel_type
        _TRANSFORMERS[panel_type] = cls
        return cls
    return decorator


def get_transformer(panel_type: str) -> BaseTransformer:
    """
    Get a transformer instance for a panel type.

    Args:
        panel_type: Grafana panel type (e.g., "stat", "timeseries")

    Returns:
        Transformer instance (falls back to StatTransformer for unknown types)
    """
    transformer_class = _TRANSFORMERS.get(panel_type)
    if transformer_class is None:
        # Fall back to stat transformer for unknown types
        from .stat import StatTransformer
        return StatTransformer()
    return transformer_class()


def get_supported_types() -> list[str]:
    """Get list of supported panel types."""
    return list(_TRANSFORMERS.keys())


# Auto-import all transformer modules to trigger registration
_transformers_dir = Path(__file__).parent
for _module_path in _transformers_dir.glob("*.py"):
    if _module_path.name not in ("__init__.py", "base.py"):
        importlib.import_module(f".{_module_path.stem}", package=__name__)

__all__ = [
    "BaseTransformer",
    "get_transformer",
    "get_supported_types",
    "register_transformer",
]
