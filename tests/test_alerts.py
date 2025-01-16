"""Tests for alert functionality"""

import json
import socket
import time
from pathlib import Path

import pytest

from src.config.models import ServerConfig
from src.monitoring.alerts import Alert, AlertLevel, AlertManager
from src.server import StringSearchServer


@pytest.fixture
def alert_manager(mock_notifier) -> AlertManager:
    """Create alert manager for testing"""
    manager = AlertManager()
    manager.add_notifier(mock_notifier)
    return manager


def test_alert_creation():
    """Test alert object creation"""
    alert = Alert(
        level=AlertLevel.WARNING,
        source="test",
        message="Test alert",
        details={"key": "value"}
    )
    
    assert alert.level == AlertLevel.WARNING
    assert alert.source == "test"
    assert alert.message == "Test alert"
    assert alert.details == {"key": "value"}
    assert alert.timestamp is not None


def test_alert_manager_creation(alert_manager: AlertManager):
    """Test alert manager creation"""
    assert len(alert_manager.notifiers) == 1
    assert len(alert_manager.alerts) == 0


def test_alert_notification(
    alert_manager: AlertManager,
    mock_notifier
):
    """Test alert notification"""
    alert = Alert(
        level=AlertLevel.WARNING,
        source="test",
        message="Test alert",
        details={"key": "value"}
    )
    
    alert_manager.send_alert(alert)
    
    assert len(mock_notifier.notifications) == 1
    assert mock_notifier.notifications[0] == alert


def test_memory_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test memory usage alert"""
    # Simulate high memory usage
    server.monitor.record_metric("memory_usage_bytes", 90 * 1024 * 1024 * 1024)  # 90GB
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    memory_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "memory"
    ]
    assert len(memory_alerts) > 0
    assert memory_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "usage" in memory_alerts[0].details


def test_cpu_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test CPU usage alert"""
    # Simulate high CPU usage
    server.monitor.record_metric("cpu_usage_percent", 95)
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    cpu_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "cpu"
    ]
    assert len(cpu_alerts) > 0
    assert cpu_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "usage" in cpu_alerts[0].details


def test_disk_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test disk usage alert"""
    # Simulate high disk usage
    server.monitor.record_metric("disk_usage_percent", 95)
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    disk_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "disk"
    ]
    assert len(disk_alerts) > 0
    assert disk_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "usage" in disk_alerts[0].details


def test_error_rate_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier,
    client: socket.socket
):
    """Test error rate alert"""
    # Generate errors
    for _ in range(100):
        client.sendall(b"invalid json\n")
        client.recv(4096)
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    error_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "error_rate"
    ]
    assert len(error_alerts) > 0
    assert error_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "rate" in error_alerts[0].details


def test_connection_pool_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test connection pool alert"""
    # Simulate high connection usage
    max_connections = server.config.resources.max_connections
    server.monitor.record_metric(
        "active_connections",
        int(max_connections * 0.9)  # 90% usage
    )
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    pool_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "connection_pool"
    ]
    assert len(pool_alerts) > 0
    assert pool_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "usage" in pool_alerts[0].details


def test_search_latency_alert(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier,
    client: socket.socket
):
    """Test search latency alert"""
    # Simulate slow search
    request = {
        "pattern": "test.*" * 100,  # Complex regex
        "options": {
            "case_sensitive": True,
            "whole_line": True,
            "regex": True
        }
    }
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    client.recv(4096)
    
    # Wait for alert check
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check alert was sent
    latency_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "search_latency"
    ]
    assert len(latency_alerts) > 0
    assert latency_alerts[0].level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
    assert "latency" in latency_alerts[0].details


def test_alert_deduplication(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test alert deduplication"""
    # Send same alert multiple times
    alert = Alert(
        level=AlertLevel.WARNING,
        source="test",
        message="Test alert",
        details={"key": "value"}
    )
    
    for _ in range(5):
        alert_manager.send_alert(alert)
        time.sleep(0.1)
    
    # Check only one notification was sent
    matching_alerts = [
        n for n in mock_notifier.notifications
        if n.source == "test" and n.message == "Test alert"
    ]
    assert len(matching_alerts) == 1


def test_alert_resolution(
    server: StringSearchServer,
    alert_manager: AlertManager,
    mock_notifier
):
    """Test alert resolution"""
    # Generate warning alert
    server.monitor.record_metric("cpu_usage_percent", 85)
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Return to normal
    server.monitor.record_metric("cpu_usage_percent", 50)
    time.sleep(server.config.monitoring.alert_check_interval + 0.1)
    
    # Check resolution alert was sent
    resolution_alerts = [
        alert for alert in mock_notifier.notifications
        if alert.source == "cpu" and "resolved" in alert.message.lower()
    ]
    assert len(resolution_alerts) > 0
    assert resolution_alerts[0].level == AlertLevel.INFO 