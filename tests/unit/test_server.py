#!/usr/bin/env python3

"""Unit tests for server functionality"""

import pytest
import socket
import time
from pathlib import Path
from server import StringSearchServer
from src.search.matcher import StringMatcher
from src.config.config import Config

@pytest.fixture
def server_config(test_data_file: Path) -> Config:
    """Create server configuration"""
    config = Config()
    config.file_path = test_data_file
    config.reread_on_query = False
    config.max_workers = 10
    config.cache_size = 100
    config.ssl_enabled = False
    config.rate_limit_enabled = False
    return config

def test_server_init(server_config: Config):
    """Test server initialization"""
    server = StringSearchServer(config=server_config)
    assert server.data is not None
    assert len(server.data) > 0

def test_search_existing(server_config: Config):
    """Test searching for existing string"""
    server = StringSearchServer(config=server_config)
    result = server.search("7;0;6;28;0;23;5;0;", "127.0.0.1")
    assert result == "STRING EXISTS"

def test_search_nonexisting(server_config: Config):
    """Test searching for non-existing string"""
    server = StringSearchServer(config=server_config)
    result = server.search("nonexistent", "127.0.0.1")
    assert result == "STRING NOT FOUND"

def test_exact_matching(server_config: Config):
    """Test exact line matching"""
    server = StringSearchServer(config=server_config)
    # Should not match partial strings
    result = server.search("7;0;6;28;0;23;5;", "127.0.0.1")
    assert result == "STRING NOT FOUND"

def test_reread_mode(test_data_file: Path):
    """Test reread on query mode"""
    config = Config()
    config.file_path = str(test_data_file)
    config.reread_on_query = True
    config.rate_limit_enabled = False
    
    server = StringSearchServer(config=config)
    
    # First search
    result1 = server.search("7;0;6;28;0;23;5;0;", "127.0.0.1")
    assert result1 == "STRING EXISTS"
    
    # Update file
    with open(test_data_file, 'a') as f:
        f.write("new_test_string\n")
        f.flush()  # Ensure write is flushed to disk
    
    # Search for new string
    result2 = server.search("new_test_string", "127.0.0.1")
    assert result2 == "STRING EXISTS", "Failed to find newly added string"

def test_performance(server_config: Config):
    """Test performance requirements"""
    server = StringSearchServer(config=server_config)
    
    start = time.perf_counter()
    server.search("7;0;6;28;0;23;5;0;", "127.0.0.1")
    duration = (time.perf_counter() - start) * 1000
    
    # Should be < 0.5ms in normal mode
    assert duration < 0.5, f"Search took {duration}ms" 