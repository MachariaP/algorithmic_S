#!/usr/bin/env python3

"""Edge case tests"""

import pytest
import socket
import time
from pathlib import Path
from server import StringSearchServer

def test_empty_query(test_server, server_port):
    """Test empty query"""
    with socket.create_connection(('localhost', server_port)) as sock:
        sock.sendall(b"\n")
        assert sock.recv(1024).strip() == b"STRING NOT FOUND"

def test_long_query(test_server, server_port):
    """Test query at max length"""
    query = "x" * 1024
    with socket.create_connection(('localhost', server_port)) as sock:
        sock.sendall(query.encode() + b"\n")
        assert sock.recv(1024).strip() == b"STRING NOT FOUND"

def test_binary_data(test_server, server_port):
    """Test binary data handling"""
    with socket.create_connection(('localhost', server_port)) as sock:
        sock.sendall(b"\x00test\x00\n")
        assert sock.recv(1024).strip() == b"STRING NOT FOUND"

def test_concurrent_file_update(test_server, server_port, test_data_file):
    """Test concurrent file updates"""
    test_server.config.reread_on_query = True
    
    with socket.create_connection(('localhost', server_port)) as sock:
        # Initial search
        sock.sendall(b"test_string\n")
        assert sock.recv(1024).strip() == b"STRING NOT FOUND"
        
        # Update file
        with open(test_data_file, 'a') as f:
            f.write("test_string\n")
            f.flush()
        
        # Search again
        sock.sendall(b"test_string\n")
        assert sock.recv(1024).strip() == b"STRING EXISTS" 