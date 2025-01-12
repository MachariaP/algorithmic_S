#!/usr/bin/env python3

"""Search functionality tests"""

import pytest
from pathlib import Path
import socket
import time

def test_server_response(host='localhost', port=44445):
    """Test server responses"""
    test_strings = [
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    ]
    
    for test in test_strings:
        # Make request
        with socket.create_connection((host, port)) as sock:
            sock.sendall(test.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            assert response == "STRING EXISTS", f"Failed for: {test}"
            
def test_nonexistent_strings(host='localhost', port=44445):
    """Test non-existent strings"""
    test_strings = [
        "nonexistent1",
        "test_string_xyz",
        "7;0;6;28;0;23;5;0"  # Missing semicolon
    ]
    
    for test in test_strings:
        with socket.create_connection((host, port)) as sock:
            sock.sendall(test.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            assert response == "STRING NOT FOUND", f"Failed for: {test}"

if __name__ == "__main__":
    pytest.main([__file__]) 