"""
Database query cache for performance optimization.
Provides caching for expensive database queries with TTL-based invalidation.
"""

import time
import hashlib
import json
from typing import Any, Callable, Optional, Dict
from functools import wraps
from inventory_app.utils.logger import logger


class QueryCache:
    """
    Simple TTL-based query cache.
    Caches database query results with configurable time-to-live.
    """

    def __init__(self, default_ttl: float = 30.0):
        """
        Initialize the query cache.

        Args:
            default_ttl: Default time-to-live in seconds (default 30 seconds)
        """
        self._cache: Dict[str, dict] = {}
        self.default_ttl = default_ttl

    def _make_key(self, query: str, params: tuple) -> str:
        """Generate a cache key from query and params."""
        key_string = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, query: str, params: tuple) -> Optional[Any]:
        """
        Get a cached result.

        Args:
            query: The SQL query
            params: Query parameters

        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(query, params)
        entry = self._cache.get(key)

        if entry is None:
            return None

        cached_time, result = entry["time"], entry["result"]
        age = time.monotonic() - cached_time

        if age > entry.get("ttl", self.default_ttl):
            del self._cache[key]
            logger.debug(f"Cache entry expired for key {key}")
            return None

        logger.debug(f"Cache hit for key {key} (age: {age:.2f}s)")
        return result

    def set(
        self, query: str, params: tuple, result: Any, ttl: Optional[float] = None
    ) -> None:
        """
        Cache a query result.

        Args:
            query: The SQL query
            params: Query parameters
            result: Result to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        key = self._make_key(query, params)
        self._cache[key] = {
            "time": time.monotonic(),
            "result": result,
            "ttl": ttl if ttl is not None else self.default_ttl,
        }
        logger.debug(f"Cached result for key {key} (ttl: {ttl or self.default_ttl}s)")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Query cache cleared")

    def invalidate(self, query_prefix: str = "") -> int:
        """
        Invalidate cache entries matching query prefix.

        Args:
            query_prefix: Prefix to match against queries

        Returns:
            Number of entries invalidated
        """
        if not query_prefix:
            count = len(self._cache)
            self.clear()
            return count

        keys_to_remove = [k for k in self._cache if query_prefix in k]
        for key in keys_to_remove:
            del self._cache[key]

        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries")
        return len(keys_to_remove)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "default_ttl": self.default_ttl,
        }


def cached_query(ttl: float = 30.0, query_name: str = ""):
    """
    Decorator for caching database query results.

    Args:
        ttl: Time-to-live in seconds
        query_name: Optional name for cache invalidation

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from inventory_app.database.connection import db

            cache = getattr(db, "_query_cache", None)
            if cache is None:
                return func(*args, **kwargs)

            if not hasattr(db, "_query_cache"):
                db._query_cache = QueryCache()

            cache = db._query_cache

            if "no_cache" in kwargs and kwargs["no_cache"]:
                return func(*args, **kwargs)

            query = kwargs.get("query", "")
            params = kwargs.get("params", ())

            if query and params:
                cached_result = cache.get(query, params)
                if cached_result is not None:
                    return cached_result

            result = func(*args, **kwargs)

            if query and params:
                cache.set(query, params, result, ttl)

            return result

        return wrapper

    return decorator


query_cache = QueryCache()
