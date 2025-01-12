#!/usr/bin/env python3

"""Comprehensive test suite"""

import pytest
import socket
import ssl
import time
import threading
import os
from pathlib import Path
from src.search.matcher import StringMatcher
from concurrent.futures import ThreadPoolExecutor
from server import StringSearchServer

@pytest.fixture
def test_server(test_config, server_port):
    """Create and start test server"""
    server = StringSearchServer(config=test_config)
    thread = threading.Thread(target=server.start, args=('localhost', server_port))
    thread.daemon = True
    thread.start()
    time.sleep(1)  # Wait for server to start
    return server

def test_exact_matching():
    """Test exact line matching"""
    test_cases = [
        ("test_string", "test_string\n", True),
        ("test_string", "test_string_extra", False),
        ("test_string", "partial_test_string", False),
        ("7;0;6;28;0;23;5;0;", "7;0;6;28;0;23;5;0;\n", True)
    ]
    
    for needle, haystack, expected in test_cases:
        assert StringMatcher.is_exact_match(needle, haystack) == expected

def test_concurrent_load(test_server, server_port):
    """Test concurrent connections"""
    def make_request():
        with socket.create_connection(('localhost', server_port)) as sock:
            sock.sendall(b"7;0;6;28;0;23;5;0;\n")
            return sock.recv(1024)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in futures]
        
    assert all(r.strip() == b"STRING EXISTS" for r in results)

def test_ssl_connection(ssl_config, server_port, ssl_certs):
    """Test SSL connection"""
    key_path, cert_path = ssl_certs
    
    # Start SSL-enabled server
    server = StringSearchServer(config=ssl_config)
    thread = threading.Thread(target=server.start, args=('localhost', server_port))
    thread.daemon = True
    thread.start()
    time.sleep(1)  # Wait for server to start
    
    # Create client SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.load_verify_locations(cafile=str(cert_path))
    
    try:
        # Connect with SSL
        with socket.create_connection(('localhost', server_port)) as sock:
            with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                ssock.sendall(b"7;0;6;28;0;23;5;0;\n")
                response = ssock.recv(1024)
                assert response.strip() == b"STRING EXISTS"
    except Exception as e:
        pytest.fail(f"SSL connection failed: {e}")

def test_file_reread(test_server, server_port, test_data_file):
    """Test file re-reading"""
    # Configure server for reread mode
    test_server.config.reread_on_query = True
    
    with socket.create_connection(('localhost', server_port)) as sock:
        # First request
        sock.sendall(b"7;0;6;28;0;23;5;0;\n")
        response = sock.recv(1024).strip()
        assert response == b"STRING EXISTS", f"Initial search failed: {response}"
        
        # Update file
        with open(test_data_file, 'a') as f:
            f.write("new_test_string\n")
            f.flush()
            os.fsync(f.fileno())  # Ensure write is synced to disk
        
        time.sleep(0.1)  # Small delay to ensure file is updated
        
        # Second request
        sock.sendall(b"new_test_string\n")
        response = sock.recv(1024).strip()
        assert response == b"STRING EXISTS", f"Search after update failed: {response}" 