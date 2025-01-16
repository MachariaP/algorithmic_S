from dataclasses import dataclass
from typing import List, Optional, Set, Dict, Tuple
from pathlib import Path
import re
import threading
import time
from .benchmark import SearchBenchmark, BenchmarkResult


@dataclass
class SearchOptions:
    """Search options configuration"""
    case_sensitive: bool = False
    whole_line_match: bool = False
    use_regex: bool = False
    invert_match: bool = False
    max_count: Optional[int] = None


@dataclass
class SearchResult:
    """Container for search results"""
    matches: List[str]
    count: int
    duration: float


class SearchEngine:
    """Search engine implementation using hash table for O(1) lookups"""
    def __init__(self):
        self.data: Set[str] = set()  # Original data
        self.lowercase_data: Set[str] = set()  # Lowercase version for case-insensitive search
        self.line_map: Dict[str, str] = {}  # Maps lowercase to original
        self._regex_cache: Dict[str, re.Pattern] = {}  # Cache compiled regex patterns
        self._result_cache: Dict[Tuple[str, str], SearchResult] = {}
        self.cache_size = 10000  # Increased cache size for better performance
        self._lock = threading.Lock()
        self.benchmark = SearchBenchmark(self)

    def load_data(self, file_path: Path) -> None:
        """Load data from file into hash table"""
        with open(file_path, 'r') as f:
            self.data = set()
            self.lowercase_data = set()
            self.line_map = {}
            for line in f:
                line = line.strip()
                if line:
                    self.data.add(line)
                    lower = line.lower()
                    self.lowercase_data.add(lower)
                    self.line_map[lower] = line

    def search(self, query: str, options: Optional[SearchOptions] = None) -> SearchResult:
        """Perform search with given options using hash table for O(1) lookups"""
        if options is None:
            options = SearchOptions()

        # Check cache first
        cache_key = (query, str(options))
        with self._lock:
            if cache_key in self._result_cache:
                return self._result_cache[cache_key]

        start_time = time.perf_counter()
        matches = []

        if not options.case_sensitive:
            query = query.lower()
            search_data = self.lowercase_data
            result_map = self.line_map
        else:
            search_data = self.data
            result_map = {line: line for line in self.data}

        # Perform search
        if options.use_regex:
            if query not in self._regex_cache:
                self._regex_cache[query] = re.compile(query)
            pattern = self._regex_cache[query]
            matches = [
                result_map[line] for line in search_data
                if bool(pattern.search(line)) != options.invert_match
            ]
        elif options.whole_line_match:
            if query in search_data:
                matches = [result_map[query]]
            if options.invert_match:
                matches = [result_map[line] for line in search_data if line != query]
        else:
            matches = [
                result_map[line] for line in search_data
                if (query in line) != options.invert_match
            ]

        if options.max_count:
            matches = matches[:options.max_count]

        duration = time.perf_counter() - start_time
        result = SearchResult(matches=matches, count=len(matches), duration=duration)

        # Update cache
        with self._lock:
            if len(self._result_cache) >= self.cache_size:
                self._result_cache.pop(next(iter(self._result_cache)))
            self._result_cache[cache_key] = result

        return result
