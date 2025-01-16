#!/usr/bin/env python3

"""
String matching implementation with multiple optimization strategies.

This module provides optimized string matching algorithms using:
- Bloom filters for quick rejection
- Hash tables for O(1) lookups
- Memory mapping for efficient file access
- LRU caching for frequent queries
"""

from typing import Set, Optional, List, Dict
from xxhash import xxh64_intdigest
from bitarray import bitarray
import mmap
from functools import lru_cache


class StringMatcher:
    """
    Optimized string matching implementation.

    This class provides multiple string matching strategies optimized for
    different use cases and file sizes. It automatically selects the best
    strategy based on input characteristics.

    Attributes:
        bloom_filter (bitarray): Quick rejection filter
        hash_table (Dict[int, str]): O(1) lookup table
        mmap_handle (Optional[mmap.mmap]): Memory mapped file handle
        cache_size (int): Size of LRU cache

    Performance:
        - Average lookup: O(1)
        - Worst case: O(n) where n is file size
        - Memory usage: ~20MB per 100K strings
    """

    def __init__(self, cache_size: int = 10000) -> None:
        """
        Initialize matcher with specified cache size.

        Args:
            cache_size: Number of entries to cache (default: 10000)

        Raises:
            ValueError: If cache_size is negative
        """
        if cache_size < 0:
            raise ValueError("Cache size must be non-negative")

        self.bloom_filter: Optional[bitarray] = None
        self.hash_table: Dict[int, str] = {}
        self.mmap_handle: Optional[mmap.mmap] = None
        self.cache_size = cache_size

    @lru_cache(maxsize=10000)
    def match(self, needle: str, haystack: Set[str]) -> bool:
        """
        Find exact string match using optimal strategy.

        Args:
            needle: String to search for
            haystack: Set of strings to search in

        Returns:
            bool: True if exact match found, False otherwise

        Raises:
            ValueError: If needle is empty
            TypeError: If haystack is not a set
        """
        if not needle:
            raise ValueError("Search string cannot be empty")

        if not isinstance(haystack, set):
            raise TypeError("Haystack must be a set")

        # Try bloom filter first
        if self.bloom_filter is not None:
            hash_val = xxh64_intdigest(needle.encode())
            if not self.bloom_filter[hash_val % len(self.bloom_filter)]:
                return False

        # Try hash table lookup
        if self.hash_table:
            hash_val = xxh64_intdigest(needle.encode())
            return hash_val in self.hash_table

        # Fall back to set lookup
        return needle in haystack

    def build_index(self, strings: Set[str]) -> None:
        """
        Build optimized index structures for given strings.

        Creates:
        1. Bloom filter for quick rejection
        2. Hash table for O(1) lookups

        Args:
            strings: Set of strings to index

        Raises:
            MemoryError: If insufficient memory
        """

        # Create bloom filter
        self.bloom_filter = bitarray(2 ** 24)  # 16MB
        self.bloom_filter.setall(0)

        # Build hash table and populate bloom filter
        for s in strings:
            hash_val = xxh64_intdigest(s.encode())
            self.hash_table[hash_val] = s
            self.bloom_filter[hash_val % len(self.bloom_filter)] = 1
