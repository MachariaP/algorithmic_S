"""Health check tests"""

import pytest
from datetime import datetime
from src.monitoring.health import HealthCheck, HealthMetrics

def test_health_check_initialization():
    """Test health check initialization"""
    health = HealthCheck()
    assert health._thresholds['cpu_percent'] == 80.0
    assert health._thresholds['memory_percent'] == 80.0
    assert health._thresholds['disk_usage_percent'] == 80.0
    assert health._thresholds['open_files'] == 1000
    assert health._thresholds['thread_count'] == 100

def test_custom_thresholds():
    """Test custom thresholds"""
    custom_thresholds = {
        'cpu_percent': 90.0,
        'memory_percent': 85.0,
        'disk_usage_percent': 75.0,
        'open_files': 500,
        'thread_count': 50
    }
    health = HealthCheck(thresholds=custom_thresholds)
    assert health._thresholds == custom_thresholds

def test_check_metrics():
    """Test metrics collection"""
    health = HealthCheck()
    metrics = health.check()
    
    assert isinstance(metrics, HealthMetrics)
    assert isinstance(metrics.cpu_percent, float)
    assert isinstance(metrics.memory_percent, float)
    assert isinstance(metrics.disk_usage_percent, float)
    assert isinstance(metrics.open_files, int)
    assert isinstance(metrics.thread_count, int)
    assert isinstance(metrics.timestamp, datetime)

def test_is_healthy():
    """Test health status check"""
    health = HealthCheck(thresholds={
        'cpu_percent': 100.0,
        'memory_percent': 100.0,
        'disk_usage_percent': 100.0,
        'open_files': 10000,
        'thread_count': 1000
    })
    assert health.is_healthy() == True

def test_history_limit():
    """Test history size limit"""
    health = HealthCheck()
    for _ in range(1100):
        health.check()
    assert len(health.get_history()) == 1000

def test_set_threshold():
    """Test threshold updates"""
    health = HealthCheck()
    health.set_threshold('cpu_percent', 95.0)
    assert health._thresholds['cpu_percent'] == 95.0
    
    with pytest.raises(ValueError):
        health.set_threshold('invalid_metric', 50.0) 