"""Tests for the search component"""

import re
from pathlib import Path

import pytest

from src.search import SearchEngine, SearchOptions


@pytest.fixture
def search_engine(test_data_file: Path) -> SearchEngine:
    """Create search engine instance"""
    engine = SearchEngine()
    engine.load_data(test_data_file)
    return engine


def test_load_data(search_engine: SearchEngine):
    """Test loading data into search engine"""
    assert len(search_engine.data) > 0
    assert all(isinstance(line, str) for line in search_engine.data)


def test_basic_search(search_engine: SearchEngine):
    """Test basic search functionality"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    results = search_engine.search("test", options)
    assert len(results.matches) > 0
    assert all("test" in line.lower() for line in results.matches)
    assert results.total_matches == len(results.matches)
    assert results.pattern == "test"


def test_case_sensitive_search(search_engine: SearchEngine):
    """Test case sensitive search"""
    options = SearchOptions(
        case_sensitive=True,
        whole_line=False,
        regex=False
    )
    
    # Search for exact case
    results = search_engine.search("test", options)
    assert len(results.matches) > 0
    assert all("test" in line for line in results.matches)
    
    # Search with different case
    results = search_engine.search("TEST", options)
    assert len(results.matches) == 0


def test_whole_line_search(search_engine: SearchEngine):
    """Test whole line search"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=True,
        regex=False
    )
    
    # Search for exact line
    results = search_engine.search("test line 1", options)
    assert len(results.matches) == 1
    assert results.matches[0] == "test line 1"
    
    # Search for partial line
    results = search_engine.search("test line", options)
    assert len(results.matches) == 0


def test_regex_search(search_engine: SearchEngine):
    """Test regex search"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=True
    )
    
    # Search with regex pattern
    results = search_engine.search(r"test.*\d", options)
    assert len(results.matches) > 0
    assert all(re.search(r"test.*\d", line, re.IGNORECASE) for line in results.matches)


def test_invalid_regex(search_engine: SearchEngine):
    """Test invalid regex pattern"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=True
    )
    
    with pytest.raises(re.error):
        search_engine.search(r"test[", options)


def test_empty_pattern(search_engine: SearchEngine):
    """Test empty search pattern"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    with pytest.raises(ValueError, match="Search pattern cannot be empty"):
        search_engine.search("", options)


def test_pattern_too_long(search_engine: SearchEngine):
    """Test pattern length limit"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    pattern = "x" * (search_engine.max_pattern_length + 1)
    with pytest.raises(ValueError, match="Search pattern too long"):
        search_engine.search(pattern, options)


def test_no_matches(search_engine: SearchEngine):
    """Test search with no matches"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    results = search_engine.search("nonexistent", options)
    assert len(results.matches) == 0
    assert results.total_matches == 0


def test_cache_hit(search_engine: SearchEngine):
    """Test search result caching"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    # First search
    results1 = search_engine.search("test", options)
    
    # Second search (should hit cache)
    results2 = search_engine.search("test", options)
    
    assert results1.matches == results2.matches
    assert results1.total_matches == results2.total_matches
    assert results1.pattern == results2.pattern


@pytest.mark.parametrize("pattern,expected_count", [
    ("test", 4),  # All lines contain "test"
    ("line", 4),  # All lines contain "line"
    ("1", 1),     # Only one line contains "1"
    ("final", 1), # Only one line contains "final"
    ("xyz", 0)    # No lines contain "xyz"
])
def test_search_counts(search_engine: SearchEngine, pattern: str, expected_count: int):
    """Test search result counts"""
    options = SearchOptions(
        case_sensitive=False,
        whole_line=False,
        regex=False
    )
    
    results = search_engine.search(pattern, options)
    assert len(results.matches) == expected_count
    assert results.total_matches == expected_count
