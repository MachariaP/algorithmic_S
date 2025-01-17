"""Integration tests for the string search server"""

import json
import socket
import threading
import time
from pathlib import Path
from typing import Generator

import pytest
import requests

from src.server import StringSearchServer
from src.config.models import ServerConfig


@pytest.fixture
def server(server_config: ServerConfig) -> Generator[StringSearchServer, None, None]:
    """Create and start server for integration tests"""
    server = StringSearchServer(server_config)
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)  # Wait for server to start
    yield server
    server.stop()


def test_full_search_flow(server: StringSearchServer, client: socket.socket):
    """Test complete search workflow"""
    # Test basic search
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    client.sendall(json.dumps(request).encode() + b"\n")
    response = json.loads(client.recv(4096).decode())
    assert "results" in response
    assert len(response["results"]) > 0

    # Test cache hit
    client.sendall(json.dumps(request).encode() + b"\n")
    response2 = json.loads(client.recv(4096).decode())
    assert response2 == response  # Should get same response from cache


def test_concurrent_searches(server: StringSearchServer):
    """Test multiple concurrent searches"""
    def client_worker(results: list):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((server.config.host, server.config.port))
            request = {
                "pattern": "test",
                "options": {"case_sensitive": False}
            }
            sock.sendall(json.dumps(request).encode() + b"\n")
            response = json.loads(sock.recv(4096).decode())
            results.append(response)

    results = []
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=client_worker, args=(results,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    assert len(results) == 10
    assert all("results" in r for r in results)


def test_metrics_endpoint(server: StringSearchServer):
    """Test metrics collection and exposure"""
    # Make some requests to generate metrics
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server.config.host, server.config.port))
        for _ in range(5):
            request = {"pattern": "test"}
            sock.sendall(json.dumps(request).encode() + b"\n")
            sock.recv(4096)

    # Check metrics endpoint
    response = requests.get(f"http://{server.config.host}:{server.config.monitoring.prometheus_port}/metrics")
    assert response.status_code == 200
    metrics = response.text

    assert "search_requests_total" in metrics
    assert "search_duration_seconds" in metrics
    assert "cache_hits_total" in metrics


def test_health_check(server: StringSearchServer):
    """Test health check endpoint"""
    response = requests.get(f"http://{server.config.host}:{server.config.monitoring.prometheus_port}/health")
    assert response.status_code == 200
    health = response.json()

    assert health["status"] == "healthy"
    assert "cpu_usage" in health
    assert "memory_usage" in health
    assert "uptime" in health


def test_rate_limiting(server: StringSearchServer):
    """Test rate limiting functionality"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server.config.host, server.config.port))
        
        # Send requests until rate limit is hit
        request = {"pattern": "test"}
        data = json.dumps(request).encode() + b"\n"
        
        responses = []
        for _ in range(server.config.security.rate_limit + 1):
            sock.sendall(data)
            response = json.loads(sock.recv(4096).decode())
            responses.append(response)
            
        # Verify rate limit was enforced
        assert any("rate_limit_exceeded" in str(r).lower() for r in responses)
        
        # Wait for rate limit window to expire
        time.sleep(60)
        
        # Verify can make requests again
        sock.sendall(data)
        response = json.loads(sock.recv(4096).decode())
        assert "rate_limit_exceeded" not in str(response).lower()


def test_ssl_connection(server: StringSearchServer):
    """Test SSL/TLS connection"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with context.wrap_socket(sock) as ssock:
            ssock.connect((server.config.host, server.config.port))
            
            request = {"pattern": "test"}
            ssock.sendall(json.dumps(request).encode() + b"\n")
            response = json.loads(ssock.recv(4096).decode())
            
            assert "results" in response


def test_data_reload(server: StringSearchServer, tmp_path: Path):
    """Test data reloading functionality"""
    # Create test data file
    data_file = tmp_path / "test_data.txt"
    data_file.write_text("initial line\n")
    
    # Update server config
    server.config.data_file = data_file
    server.load_data()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server.config.host, server.config.port))
        
        # Test initial data
        request = {"pattern": "initial"}
        sock.sendall(json.dumps(request).encode() + b"\n")
        response = json.loads(sock.recv(4096).decode())
        assert len(response["results"]) == 1
        
        # Update data file
        data_file.write_text("new line\n")
        server.load_data()
        
        # Test updated data
        request = {"pattern": "new"}
        sock.sendall(json.dumps(request).encode() + b"\n")
        response = json.loads(sock.recv(4096).decode())
        assert len(response["results"]) == 1 