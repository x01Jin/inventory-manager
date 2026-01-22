"""
Database query cache for performance optimization.
Provides caching for expensive database queries with TTL-based invalidation.
Supports table-based invalidation and query classification for optimal caching.
"""

import time
import hashlib
import json
import re
from typing import Any, Callable, Optional, Dict, Set, List
from functools import wraps
from collections import OrderedDict
from inventory_app.utils.logger import logger


class QueryCache:
    """
    TTL-based query cache with table tracking and intelligent invalidation.
    Optimized for HDD-based systems with multi-level TTL strategy.
    """

    # TTL categories in seconds
    TTL_INVENTORY = 10.0  # Inventory/Requisition Data
    TTL_REFERENCE = 60.0  # Reference Data (categories, suppliers)
    TTL_STATISTICS = 30.0  # Statistics/Aggregates
    TTL_USER = 5.0  # User-Specific Queries
    TTL_DEFAULT = 30.0  # Default TTL

    # Maximum cache settings
    MAX_CACHE_SIZE = 10000  # Maximum entries
    MAX_CACHE_MEMORY_MB = 100  # Maximum memory in MB

    def __init__(self, default_ttl: float = TTL_DEFAULT):
        """
        Initialize the query cache.

        Args:
            default_ttl: Default time-to-live in seconds (default 30 seconds)
        """
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._table_entries: Dict[str, Set[str]] = {}  # table_name -> set of cache_keys
        self.default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "invalidations": 0,
        }
        self._query_classifier = QueryClassifier()

    def _make_key(self, query: str, params: tuple) -> str:
        """Generate a cache key from query and params."""
        key_string = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _classify_query(self, query: str) -> str:
        """
        Classify query type for optimal TTL assignment.

        Args:
            query: SQL query string

        Returns:
            Query classification category
        """
        return self._query_classifier.classify(query)

    def _get_ttl_for_query(self, query: str) -> float:
        """
        Get TTL based on query classification.

        Args:
            query: SQL query string

        Returns:
            TTL in seconds
        """
        classification = self._classify_query(query)

        ttl_map = {
            "inventory": self.TTL_INVENTORY,
            "requisition": self.TTL_INVENTORY,
            "reference": self.TTL_REFERENCE,
            "statistics": self.TTL_STATISTICS,
            "user": self.TTL_USER,
            "uncacheable": 0,  # Never cache
        }

        return ttl_map.get(classification, self.default_ttl)

    def _estimate_size(self, result: Any) -> int:
        """
        Estimate memory size of a cached result.

        Args:
            result: The result to estimate size for

        Returns:
            Estimated size in bytes
        """
        try:
            if isinstance(result, (list, dict)):
                return len(json.dumps(result, default=str).encode())
            return len(str(result).encode())
        except Exception:
            return 100  # Conservative estimate

    def _evict_lru(self) -> bool:
        """
        Evict least recently used entries when cache is full.

        Returns:
            True if eviction occurred, False otherwise
        """
        while len(self._cache) >= self.MAX_CACHE_SIZE:
            try:
                lru_key, _ = self._cache.popitem(last=False)
                self._remove_from_table_index(lru_key)
                self._stats["evictions"] += 1
                logger.debug(f"Evicted LRU cache entry: {lru_key[:16]}...")
                return True
            except KeyError:
                break
        return False

    def _add_to_table_index(self, key: str, tables: Set[str]) -> None:
        """Add cache key to table index for fast invalidation."""
        for table in tables:
            if table not in self._table_entries:
                self._table_entries[table] = set()
            self._table_entries[table].add(key)

    def _remove_from_table_index(self, key: str) -> None:
        """Remove cache key from table index."""
        tables_to_remove = []
        for table, keys in self._table_entries.items():
            if key in keys:
                keys.discard(key)
                if not keys:
                    tables_to_remove.append(table)

        # Clean up empty table entries
        for table in tables_to_remove:
            del self._table_entries[table]

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
            self._stats["misses"] += 1
            return None

        cached_time, result, ttl, _ = (
            entry["time"],
            entry["result"],
            entry["ttl"],
            entry.get("tables", set()),
        )
        age = time.monotonic() - cached_time

        if age > ttl:
            del self._cache[key]
            self._remove_from_table_index(key)
            self._stats["misses"] += 1
            logger.debug(f"Cache entry expired for key {key[:16]}... (age: {age:.2f}s)")
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)

        self._stats["hits"] += 1
        logger.debug(f"Cache hit for key {key[:16]}... (age: {age:.2f}s)")
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
            ttl: Time-to-live in seconds (uses classification if not specified)
        """
        # Determine TTL
        if ttl is None:
            ttl = self._get_ttl_for_query(query)

        # Don't cache if TTL is 0 (uncacheable queries)
        if ttl <= 0:
            return

        # Extract tables from query for invalidation
        tables = self._query_classifier.extract_tables(query)

        key = self._make_key(query, params)

        # Evict if at capacity
        while len(self._cache) >= self.MAX_CACHE_SIZE:
            if not self._evict_lru():
                break

        # Remove existing entry if present
        if key in self._cache:
            self._remove_from_table_index(key)

        self._cache[key] = {
            "time": time.monotonic(),
            "result": result,
            "ttl": ttl,
            "tables": tables,
        }

        self._add_to_table_index(key, tables)
        self._stats["sets"] += 1
        logger.debug(
            f"Cached result for key {key[:16]}... (ttl: {ttl:.1f}s, tables: {tables})"
        )

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._cache)
        self._cache.clear()
        self._table_entries.clear()
        logger.debug(f"Query cache cleared ({count} entries removed)")

    def invalidate(self, table_name: str = "") -> int:
        """
        Invalidate cache entries related to a specific table.

        Args:
            table_name: Name of the table to invalidate cache for (case-insensitive)

        Returns:
            Number of entries invalidated
        """
        if not table_name:
            count = len(self._cache)
            self.clear()
            self._stats["invalidations"] += count
            return count

        table_name_lower = table_name.lower()
        keys = self._table_entries.get(table_name_lower, set()).copy()
        for key in keys:
            if key in self._cache:
                del self._cache[key]
                self._remove_from_table_index(key)

        count = len(keys)
        self._stats["invalidations"] += count
        logger.debug(f"Invalidated {count} cache entries for table '{table_name}'")
        return count

    def invalidate_multiple(self, tables: List[str]) -> int:
        """
        Invalidate cache entries for multiple tables.

        Args:
            tables: List of table names to invalidate

        Returns:
            Total number of entries invalidated
        """
        total = 0
        for table in tables:
            total += self.invalidate(table)
        return total

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.MAX_CACHE_SIZE,
            "default_ttl": self.default_ttl,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "sets": self._stats["sets"],
            "evictions": self._stats["evictions"],
            "invalidations": self._stats["invalidations"],
            "table_entries": len(self._table_entries),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "invalidations": 0,
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = time.monotonic()
        keys_to_remove = []

        for key, entry in self._cache.items():
            age = now - entry["time"]
            if age > entry["ttl"]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            self._remove_from_table_index(key)

        count = len(keys_to_remove)
        if count > 0:
            logger.debug(f"Cleaned up {count} expired cache entries")
        return count


class QueryClassifier:
    """
    Classifies SQL queries for optimal caching strategy.
    Identifies query type and extracts affected tables.
    """

    # Patterns for query classification
    QUERY_PATTERNS = {
        "inventory": [
            r"SELECT.*FROM\s+Items",
            r"SELECT.*FROM\s+Item_Batches",
            r"SELECT.*FROM\s+Stock_Movements",
            r"SELECT.*FROM\s+inventory",
        ],
        "requisition": [
            r"SELECT.*FROM\s+Requisitions",
            r"SELECT.*FROM\s+Requisition_Items",
            r"SELECT.*FROM\s+requisition",
        ],
        "reference": [
            r"SELECT.*FROM\s+Categories",
            r"SELECT.*FROM\s+Suppliers",
            r"SELECT.*FROM\s+Requesters",
            r"SELECT.*FROM\s+Users",
            r"SELECT.*FROM\s+Departments",
        ],
        "statistics": [
            r"SELECT\s+COUNT\(",
            r"SELECT\s+SUM\(",
            r"SELECT\s+AVG\(",
            r"SELECT\s+MIN\(",
            r"SELECT\s+MAX\(",
            r"SELECT.*GROUP\s+BY",
            r"SELECT.*HAVING",
        ],
        "user": [
            r"WHERE\s+user_id",
            r"WHERE\s+requester_id",
        ],
    }

    # Non-cacheable patterns (large LIMIT/OFFSET, leading wildcard searches)
    UNCACHEABLE_PATTERNS = [
        r"LIMIT\s+[1-9]\d{3,}",  # LIMIT > 1000 (pagination that might change)
        r"OFFSET\s+\d+",
    ]

    # Pattern to match small LIMITs (which are cacheable)
    SMALL_LIMIT_PATTERN = re.compile(r"LIMIT\s+(\d+)", re.IGNORECASE)

    # Table extraction patterns
    TABLE_PATTERN = re.compile(
        r"(?:FROM|JOIN|INTO|UPDATE)\s+`?(\w+)`?", re.IGNORECASE | re.MULTILINE
    )

    def __init__(self):
        """Initialize the query classifier."""
        self._patterns = {}
        for category, patterns in self.QUERY_PATTERNS.items():
            self._patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._uncacheable = [
            re.compile(p, re.IGNORECASE) for p in self.UNCACHEABLE_PATTERNS
        ]

    def classify(self, query: str) -> str:
        """
        Classify a query into a category.

        Args:
            query: SQL query string

        Returns:
            Query classification category
        """
        # Check if uncacheable
        for pattern in self._uncacheable:
            if pattern.search(query):
                return "uncacheable"

        # Classify based on patterns
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    return category

        return "default"

    def extract_tables(self, query: str) -> Set[str]:
        """
        Extract table names from a query.

        Args:
            query: SQL query string

        Returns:
            Set of table names
        """
        tables = set()
        matches = self.TABLE_PATTERN.findall(query)
        for match in matches:
            table = match.lower()
            # Filter out SQLite internal tables
            if not table.startswith("sqlite_") and table not in ("main", "temp"):
                tables.add(table)
        return tables

    def is_cacheable(self, query: str) -> bool:
        """
        Check if a query is cacheable.

        Args:
            query: SQL query string

        Returns:
            True if cacheable, False otherwise
        """
        # Check uncacheable patterns first
        for pattern in self._uncacheable:
            if pattern.search(query):
                return False

        # Check for small LIMIT (which is OK to cache)
        limit_match = self.SMALL_LIMIT_PATTERN.search(query)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value <= 100:
                return True
            return False

        return True


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
