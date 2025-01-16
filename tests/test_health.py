"""Tests for health check functionality"""

import json
import socket
import time
from pathlib import Path

import pytest
import requests

from src.config.models import ServerConfig
from src.monitoring.health import HealthCheck, HealthStatus
from src.server import StringSearchServer


@pytest.fixture
def health_url(server_config: ServerConfig) -> str:
    """Get health check endpoint URL"""
    return f"http://{server_config.host}:{server_config.monitoring.prometheus_port}/health"


def test_health_check_endpoint(
    server: StringSearchServer,
    health_url: str
):
    """Test health check endpoint"""
    response = requests.get(health_url)
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_memory_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test memory health check"""
    response = requests.get(health_url)
    data = response.json()
    
    memory_check = next(
        check for check in data["checks"]
        if check["name"] == "memory"
    )
    assert memory_check["status"] in ["healthy", "warning", "critical"]
    assert "usage_percent" in memory_check["details"]
    assert "threshold_percent" in memory_check["details"]


def test_cpu_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test CPU health check"""
    response = requests.get(health_url)
    data = response.json()
    
    cpu_check = next(
        check for check in data["checks"]
        if check["name"] == "cpu"
    )
    assert cpu_check["status"] in ["healthy", "warning", "critical"]
    assert "usage_percent" in cpu_check["details"]
    assert "threshold_percent" in cpu_check["details"]


def test_disk_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test disk health check"""
    response = requests.get(health_url)
    data = response.json()
    
    disk_check = next(
        check for check in data["checks"]
        if check["name"] == "disk"
    )
    assert disk_check["status"] in ["healthy", "warning", "critical"]
    assert "usage_percent" in disk_check["details"]
    assert "threshold_percent" in disk_check["details"]


def test_search_engine_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test search engine health check"""
    response = requests.get(health_url)
    data = response.json()
    
    search_check = next(
        check for check in data["checks"]
        if check["name"] == "search_engine"
    )
    assert search_check["status"] in ["healthy", "warning", "critical"]
    assert "last_search_time" in search_check["details"]
    assert "error_rate" in search_check["details"]


def test_connection_pool_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test connection pool health check"""
    response = requests.get(health_url)
    data = response.json()
    
    pool_check = next(
        check for check in data["checks"]
        if check["name"] == "connection_pool"
    )
    assert pool_check["status"] in ["healthy", "warning", "critical"]
    assert "active_connections" in pool_check["details"]
    assert "max_connections" in pool_check["details"]


def test_file_descriptor_health_check(
    server: StringSearchServer,
    health_url: str
):
    """Test file descriptor health check"""
    response = requests.get(health_url)
    data = response.json()
    
    fd_check = next(
        check for check in data["checks"]
        if check["name"] == "file_descriptors"
    )
    assert fd_check["status"] in ["healthy", "warning", "critical"]
    assert "used_descriptors" in fd_check["details"]
    assert "max_descriptors" in fd_check["details"]


def test_overall_health_status(
    server: StringSearchServer,
    health_url: str
):
    """Test overall health status"""
    response = requests.get(health_url)
    data = response.json()
    
    assert data["status"] in ["healthy", "warning", "critical"]
    assert len(data["checks"]) > 0
    
    # Overall status should be the worst status of any check
    check_statuses = [check["status"] for check in data["checks"]]
    if "critical" in check_statuses:
        assert data["status"] == "critical"
    elif "warning" in check_statuses:
        assert data["status"] == "warning"
    else:
        assert data["status"] == "healthy"


@pytest.mark.slow
def test_health_check_interval(
    server: StringSearchServer,
    health_url: str
):
    """Test health check interval"""
    # Get initial health data
    response = requests.get(health_url)
    initial_data = response.json()
    
    # Wait for health check interval
    time.sleep(server.config.monitoring.health_check_interval + 0.1)
    
    # Get updated health data
    response = requests.get(health_url)
    updated_data = response.json()
    
    # Check timestamps are different
    assert any(
        initial_check["timestamp"] != updated_check["timestamp"]
        for initial_check, updated_check in zip(
            initial_data["checks"],
            updated_data["checks"]
        )
    ) 