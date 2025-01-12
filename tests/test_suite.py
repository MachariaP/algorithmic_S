#!/usr/bin/env python3

"""
Comprehensive test suite for String Search Server

Tests:
1. Data file integrity
2. Server functionality
3. Client operations
4. Performance metrics
"""

import pytest
import socket
import time
import logging
from pathlib import Path
import statistics
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)

# Test data
TEST_STRINGS = {
    "7;0;6;28;0;23;5;0;",
    "1;0;6;16;0;19;3;0;",
    "18;0;21;26;0;17;3;0;",
    "20;0;1;11;0;12;5;0;"
}

def test_data_file():
    """Test data file existence and content"""
    data_path = Path("data/200k.txt")
    assert data_path.exists(), "Data file missing"
    
    with open(data_path, 'r') as f:
        content = set(line.strip() for line in f if line.strip())
        
    # Check test strings
    for test in TEST_STRINGS:
        assert test in content, f"Missing test string: {test}"
        
def test_server_connection():
    """Test server connection"""
    with socket.create_connection(('localhost', 44445)) as sock:
        assert sock.getsockname(), "Failed to connect to server"

def test_search_existing():
    """Test searching for existing strings"""
    for test in TEST_STRINGS:
        with socket.create_connection(('localhost', 44445)) as sock:
            sock.sendall(test.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            assert response == "STRING EXISTS", f"Failed for: {test}"

def test_search_nonexisting():
    """Test searching for non-existing strings"""
    test_strings = [
        "nonexistent1",
        "test_string_xyz",
        "invalid;format"
    ]
    
    for test in test_strings:
        with socket.create_connection(('localhost', 44445)) as sock:
            sock.sendall(test.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            assert response == "STRING NOT FOUND", f"Failed for: {test}"

def test_concurrent_requests():
    """Test concurrent requests"""
    def make_request(test_string):
        with socket.create_connection(('localhost', 44445)) as sock:
            sock.sendall(test_string.encode() + b'\n')
            return sock.recv(1024).decode().strip()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_request, test)
            for test in TEST_STRINGS
            for _ in range(10)  # 10 requests per string
        ]
        
        results = [f.result() for f in futures]
        assert all(r == "STRING EXISTS" for r in results), "Concurrent requests failed"

def test_performance():
    """Test performance metrics"""
    test_string = next(iter(TEST_STRINGS))
    times = []
    
    for _ in range(100):
        start = time.perf_counter()
        with socket.create_connection(('localhost', 44445)) as sock:
            sock.sendall(test_string.encode() + b'\n')
            response = sock.recv(1024)
        duration = (time.perf_counter() - start) * 1000  # ms
        times.append(duration)
    
    avg_time = statistics.mean(times)
    assert avg_time < 10, f"Average response time too high: {avg_time:.2f}ms"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 