"""Tests for the server component"""

import json
import socket
import time
from pathlib import Path

import pytest

from src.server import StringSearchServer
from src.config.models import ServerConfig


def test_server_creation(server_config: ServerConfig):
    """Test server can be created"""
    server = StringSearchServer(server_config)
    assert server.config == server_config
    assert not server.is_running


def test_server_start_stop(server: StringSearchServer):
    """Test server start and stop"""
    assert server.is_running
    server.stop()
    assert not server.is_running


def test_server_connection(server: StringSearchServer, client: socket.socket):
    """Test client can connect to server"""
    assert client.getpeername() == (server.config.host, server.config.port)


def test_search_request(server: StringSearchServer, client: socket.socket):
    """Test basic search request"""
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    
    # Send request
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    
    # Receive response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "results" in response
    assert len(response["results"]) > 0
    assert all("test" in result.lower() for result in response["results"])
    assert "request_id" in response


def test_invalid_json(server: StringSearchServer, client: socket.socket):
    """Test invalid JSON request"""
    # Send invalid JSON
    client.sendall(b"invalid json\n")
    
    # Receive error response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "error" in response
    assert response["error"]["code"] == "INVALID_REQUEST"
    assert "Invalid JSON" in response["error"]["message"]


def test_missing_pattern(server: StringSearchServer, client: socket.socket):
    """Test request without pattern"""
    request = {
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    
    # Send request
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    
    # Receive error response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "error" in response
    assert response["error"]["code"] == "INVALID_REQUEST"
    assert "Missing pattern" in response["error"]["message"]


def test_invalid_regex(server: StringSearchServer, client: socket.socket):
    """Test invalid regex pattern"""
    request = {
        "pattern": "[",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": True
        }
    }
    
    # Send request
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    
    # Receive error response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "error" in response
    assert response["error"]["code"] == "INVALID_PATTERN"
    assert "Invalid regex" in response["error"]["message"]


def test_pattern_too_long(server: StringSearchServer, client: socket.socket):
    """Test pattern length limit"""
    request = {
        "pattern": "x" * (server.config.search.max_pattern_length + 1),
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    
    # Send request
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    
    # Receive error response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "error" in response
    assert response["error"]["code"] == "INVALID_PATTERN"
    assert "Pattern too long" in response["error"]["message"]


def test_rate_limit(server: StringSearchServer, client: socket.socket):
    """Test rate limiting"""
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    data = json.dumps(request).encode() + b"\n"
    
    # Send requests until rate limit exceeded
    rate_limit = server.config.security.rate_limit
    for _ in range(rate_limit + 1):
        client.sendall(data)
        response = client.recv(4096)
        response = json.loads(response.decode())
        
        if "error" in response:
            assert response["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            break
    else:
        pytest.fail("Rate limit was not enforced")


def test_max_connections(server_config: ServerConfig):
    """Test maximum connections limit"""
    server = StringSearchServer(server_config)
    server.start()
    
    clients = []
    try:
        # Create connections until max reached
        for _ in range(server_config.resources.max_connections + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if server_config.security.ssl_enabled:
                ssl_wrapper = SSLWrapper(server_config.security)
                sock = ssl_wrapper.wrap_socket(sock, server_side=False)
                
            try:
                sock.connect((server_config.host, server_config.port))
                clients.append(sock)
            except (ConnectionRefusedError, OSError):
                break
        else:
            pytest.fail("Connection limit was not enforced")
            
    finally:
        for client in clients:
            client.close()
        server.stop()


def test_connection_timeout(server: StringSearchServer, client: socket.socket):
    """Test connection timeout"""
    # Wait for timeout
    time.sleep(server.config.resources.connection_timeout + 0.1)
    
    # Try to send request
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    data = json.dumps(request).encode() + b"\n"
    
    with pytest.raises(BrokenPipeError):
        client.sendall(data)


def test_request_too_large(server: StringSearchServer, client: socket.socket):
    """Test request size limit"""
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        },
        "data": "x" * server.config.resources.max_request_size
    }
    
    # Send request
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    
    # Receive error response
    response = client.recv(4096)
    response = json.loads(response.decode())
    
    assert "error" in response
    assert response["error"]["code"] == "REQUEST_TOO_LARGE"
