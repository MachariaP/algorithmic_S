#!/usr/bin/env python3

"""Server tests"""

import pytest
import socket
import time
from pathlib import Path
from server import StringSearchServer
from src.config.config import Config

def test_data_exists():
    """Test data file exists"""
    assert Path("data/200k.txt").exists()

def test_server_response():
    """Test server response for known strings"""
    test_strings = [
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    ]
    
    server = StringSearchServer()
    for test in test_strings:
        response = server.search(test, "127.0.0.1")
        assert response == "STRING EXISTS", f"Failed for: {test}"

def test_performance():
    """Test performance requirements"""
    server = StringSearchServer()
    
    # Test normal mode
    start = time.perf_counter()
    server.search("7;0;6;28;0;23;5;0;", "127.0.0.1")
    duration = (time.perf_counter() - start) * 1000
    assert duration < 0.5, f"Normal mode too slow: {duration}ms"
    
    # Test reread mode
    server.config.reread_on_query = True
    start = time.perf_counter()
    server.search("7;0;6;28;0;23;5;0;", "127.0.0.1")
    duration = (time.perf_counter() - start) * 1000
    assert duration < 40, f"Reread mode too slow: {duration}ms"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
   