"""
Feature flags for gradual rollout of performance optimizations.

Chunk 6: Virtual Scrolling Migration Strategy

Phase 1: Dual Implementation (Current)
- Keep existing QTableWidget implementation
- Add VirtualTableModel alongside
- Feature flag to toggle between modes
- Test both implementations

Phase 2: Gradual Rollout
- Enable virtual scrolling for users with >1000 items
- Monitor performance and user feedback
- Fix any issues in virtual mode
- Keep fallback available

Phase 3: Full Migration
- Make virtual scrolling the default
- Remove legacy code after stability confirmed
- Optimize for virtual-only operation
"""

from typing import Dict, Any, Optional
from inventory_app.utils.logger import logger


class FeatureFlags:
    """Feature flag management for performance optimizations."""

    _instance: Optional["FeatureFlags"] = None
    _flags: Dict[str, Any] = {}

    def __new__(cls) -> "FeatureFlags":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize default feature flags."""
        self._flags = {
            "virtual_scrolling": {
                "enabled": False,
                "min_row_count": 1000,
                "use_fallback": True,
                "description": "Enable virtual scrolling for large datasets",
            },
            "parallel_loading": {
                "enabled": True,
                "description": "Enable parallel data loading (Chunk 5)",
            },
            "query_caching": {
                "enabled": True,
                "description": "Enable query caching (Chunk 1)",
            },
            "batched_status": {
                "enabled": True,
                "description": "Enable batched status queries (Chunk 2)",
            },
            "progressive_styling": {
                "enabled": True,
                "description": "Enable progressive row styling (Chunk 3)",
            },
            "batch_tuning": {
                "enabled": True,
                "description": "Enable batch size tuning (Chunk 4)",
            },
            "debug_mode": {
                "enabled": False,
                "description": "Enable debug logging for performance",
            },
        }

    @classmethod
    def instance(cls) -> "FeatureFlags":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get a feature flag value."""
        if key in self._flags:
            if isinstance(self._flags[key], dict):
                return self._flags[key].get("enabled", default)
            return self._flags[key]
        return default

    def get_config(self, key: str) -> Dict[str, Any]:
        """Get full config for a feature."""
        return self._flags.get(key, {})

    def set(self, key: str, value: Any) -> None:
        """Set a feature flag value."""
        if key in self._flags and isinstance(self._flags[key], dict):
            self._flags[key]["enabled"] = value
            logger.info(f"Feature flag '{key}' set to {value}")
        elif key in self._flags:
            self._flags[key] = value
            logger.info(f"Feature flag '{key}' set to {value}")

    def set_config(self, key: str, config: Dict[str, Any]) -> None:
        """Set full config for a feature."""
        self._flags[key] = config
        logger.info(f"Feature config '{key}' updated")

    def should_use_virtual_scrolling(self, row_count: int = 0) -> bool:
        """Check if virtual scrolling should be used."""
        if not self.get("virtual_scrolling"):
            return False

        config = self.get_config("virtual_scrolling")
        min_rows = config.get("min_row_count", 1000)

        return row_count >= min_rows

    def is_fallback_mode(self) -> bool:
        """Check if fallback mode is enabled."""
        config = self.get_config("virtual_scrolling")
        return config.get("use_fallback", True)


feature_flags = FeatureFlags.instance()


VIRTUAL_SCROLLING_ENABLED = feature_flags.get("virtual_scrolling")
VIRTUAL_SCROLLING_MIN_ROWS = feature_flags.get_config("virtual_scrolling").get(
    "min_row_count", 1000
)
PARALLEL_LOADING_ENABLED = feature_flags.get("parallel_loading")
QUERY_CACHING_ENABLED = feature_flags.get("query_caching")
BATCHED_STATUS_ENABLED = feature_flags.get("batched_status")
PROGRESSIVE_STYLING_ENABLED = feature_flags.get("progressive_styling")
BATCH_TUNING_ENABLED = feature_flags.get("batch_tuning")
DEBUG_MODE = feature_flags.get("debug_mode")
