#!/usr/bin/env python3

"""
Monitoring Tests

This module tests monitoring functionality:
1. Performance metrics
2. Health checks
3. Alerting
4. Logging
5. Reporting
"""

import pytest
import socket
import threading
import time
import json
import logging
import tempfile
import os
from pathlib import Path
from typing import Generator, Dict, Any, List
from unittest.mock import patch, MagicMock

from src.monitoring import PerformanceMonitor, HealthCheck, AlertManager
from src.server import StringSearchServer


@pytest.fixture
def server() -> Generator[StringSearchServer, None, None]:
    """Fixture to create and start server for tests"""
    server = StringSearchServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)  # Wait for server to start
    yield server
    server.sock.close()


@pytest.fixture
def monitor(server: StringSearchServer) -> Generator[PerformanceMonitor, None, None]:
    """Fixture to create performance monitor"""
    monitor = PerformanceMonitor(server)
    yield monitor


class TestPerformanceMetrics:
    """Test performance metrics collection"""

    def test_basic_metrics(self, monitor: PerformanceMonitor) -> None:
        """Test basic metrics collection"""
        metrics = monitor.get_metrics()
        
        # Verify required metrics exist
        assert "requests_per_second" in metrics
        assert "average_response_time" in metrics
        assert "error_rate" in metrics
        assert "cache_hit_rate" in metrics
        assert "memory_usage" in metrics
        assert "cpu_usage" in metrics
        
        # Verify metric types
        assert isinstance(metrics["requests_per_second"], float)
        assert isinstance(metrics["average_response_time"], float)
        assert isinstance(metrics["error_rate"], float)
        assert isinstance(metrics["cache_hit_rate"], float)
        assert isinstance(metrics["memory_usage"], float)
        assert isinstance(metrics["cpu_usage"], float)

    def test_metrics_under_load(self, server: StringSearchServer, monitor: PerformanceMonitor) -> None:
        """Test metrics collection under load"""
        def generate_load() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(1000):
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Start load thread
        load_thread = threading.Thread(target=generate_load)
        load_thread.start()

        # Collect metrics during load
        metrics_samples = []
        start_time = time.time()
        while load_thread.is_alive():
            metrics_samples.append(monitor.get_metrics())
            time.sleep(0.1)

        load_thread.join()

        # Verify metrics reflect load
        assert any(m["requests_per_second"] > 0 for m in metrics_samples)
        assert any(m["cpu_usage"] > 0 for m in metrics_samples)
        assert any(m["memory_usage"] > 0 for m in metrics_samples)

    def test_metrics_export(self, monitor: PerformanceMonitor) -> None:
        """Test metrics export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            # Export metrics
            metrics = monitor.get_metrics()
            monitor.export_metrics(temp_file.name)
            
            # Verify exported file
            with open(temp_file.name, 'r') as f:
                exported_metrics = json.load(f)
                assert exported_metrics == metrics

            os.unlink(temp_file.name)


class TestHealthChecks:
    """Test health check functionality"""

    def test_basic_health_check(self, server: StringSearchServer) -> None:
        """Test basic health check"""
        health_check = HealthCheck(server)
        status = health_check.check_health()
        
        assert status["status"] == "healthy"
        assert "uptime" in status
        assert "memory_usage" in status
        assert "cpu_usage" in status
        assert "open_connections" in status

    def test_component_health_checks(self, server: StringSearchServer) -> None:
        """Test individual component health checks"""
        health_check = HealthCheck(server)
        
        # Test server health
        assert health_check.check_server_health()["status"] == "healthy"
        
        # Test cache health
        assert health_check.check_cache_health()["status"] == "healthy"
        
        # Test search engine health
        assert health_check.check_search_health()["status"] == "healthy"

    def test_health_check_thresholds(self, server: StringSearchServer) -> None:
        """Test health check thresholds"""
        health_check = HealthCheck(server)
        
        # Test with different memory thresholds
        with patch.object(health_check, 'memory_threshold', 1):  # 1MB threshold
            status = health_check.check_health()
            assert status["status"] == "unhealthy"
            assert "high memory usage" in status["details"]

        # Test with different CPU thresholds
        with patch.object(health_check, 'cpu_threshold', 1):  # 1% threshold
            status = health_check.check_health()
            assert status["status"] == "unhealthy"
            assert "high cpu usage" in status["details"]


class TestAlerting:
    """Test alerting functionality"""

    def test_alert_triggers(self, server: StringSearchServer) -> None:
        """Test alert triggers"""
        alert_manager = AlertManager(server)
        
        # Test high CPU alert
        with patch('psutil.Process.cpu_percent', return_value=95):
            alerts = alert_manager.check_alerts()
            assert any("cpu usage" in alert.lower() for alert in alerts)

        # Test high memory alert
        with patch('psutil.Process.memory_info') as mock_memory:
            mock_memory.return_value.rss = 1024 * 1024 * 1024  # 1GB
            alerts = alert_manager.check_alerts()
            assert any("memory usage" in alert.lower() for alert in alerts)

        # Test high error rate alert
        with patch.object(server, 'error_count', 1000):
            alerts = alert_manager.check_alerts()
            assert any("error rate" in alert.lower() for alert in alerts)

    def test_alert_history(self, server: StringSearchServer) -> None:
        """Test alert history management"""
        alert_manager = AlertManager(server)
        
        # Generate some alerts
        with patch('psutil.Process.cpu_percent', return_value=95):
            alert_manager.check_alerts()
        
        # Verify alert history
        history = alert_manager.get_alert_history()
        assert len(history) > 0
        assert all(isinstance(alert, dict) for alert in history)
        assert all("timestamp" in alert for alert in history)
        assert all("message" in alert for alert in history)
        assert all("severity" in alert for alert in history)

    def test_alert_notifications(self, server: StringSearchServer) -> None:
        """Test alert notifications"""
        mock_notifier = MagicMock()
        alert_manager = AlertManager(server, notifier=mock_notifier)
        
        # Generate alert
        with patch('psutil.Process.cpu_percent', return_value=95):
            alert_manager.check_alerts()
        
        # Verify notification was sent
        assert mock_notifier.send_notification.called
        args = mock_notifier.send_notification.call_args[0]
        assert "cpu usage" in args[0].lower()


class TestLogging:
    """Test logging functionality"""

    def test_log_format(self, server: StringSearchServer) -> None:
        """Test log message format"""
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            # Configure logging
            logging.basicConfig(
                filename=temp_file.name,
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Generate some activity
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                sock.recv(1024)
            
            # Verify log format
            with open(temp_file.name, 'r') as f:
                log_lines = f.readlines()
                assert len(log_lines) > 0
                for line in log_lines:
                    assert " - " in line
                    assert any(level in line for level in ["DEBUG", "INFO", "WARNING", "ERROR"])

    def test_log_levels(self, server: StringSearchServer) -> None:
        """Test different log levels"""
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            # Configure logging
            logger = logging.getLogger('string_search_server')
            handler = logging.FileHandler(temp_file.name)
            logger.addHandler(handler)
            
            # Log messages at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Verify log messages
            with open(temp_file.name, 'r') as f:
                log_content = f.read()
                assert "Debug message" in log_content
                assert "Info message" in log_content
                assert "Warning message" in log_content
                assert "Error message" in log_content

    def test_log_rotation(self, server: StringSearchServer) -> None:
        """Test log rotation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"
            
            # Configure rotating log handler
            logger = logging.getLogger('string_search_server')
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=1024,
                backupCount=3
            )
            logger.addHandler(handler)
            
            # Generate enough logs to trigger rotation
            for i in range(1000):
                logger.info(f"Test log message {i}")
            
            # Verify log files
            log_files = list(Path(temp_dir).glob("server.log*"))
            assert len(log_files) > 1


class TestReporting:
    """Test reporting functionality"""

    def test_performance_report(self, monitor: PerformanceMonitor) -> None:
        """Test performance report generation"""
        # Generate some load
        def generate_load() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(1000):
                    sock.send(b"test\n")
                    sock.recv(1024)

        load_thread = threading.Thread(target=generate_load)
        load_thread.start()

        # Collect metrics
        metrics_samples = []
        while load_thread.is_alive():
            metrics_samples.append(monitor.get_metrics())
            time.sleep(0.1)

        load_thread.join()

        # Generate report
        report = monitor.generate_report(metrics_samples)
        
        # Verify report contents
        assert "summary" in report
        assert "detailed_metrics" in report
        assert "recommendations" in report
        assert isinstance(report["summary"], dict)
        assert isinstance(report["detailed_metrics"], list)
        assert isinstance(report["recommendations"], list)

    def test_health_report(self, server: StringSearchServer) -> None:
        """Test health report generation"""
        health_check = HealthCheck(server)
        
        # Generate health report
        report = health_check.generate_report()
        
        # Verify report contents
        assert "overall_status" in report
        assert "component_status" in report
        assert "issues" in report
        assert isinstance(report["component_status"], dict)
        assert isinstance(report["issues"], list)

    def test_alert_report(self, server: StringSearchServer) -> None:
        """Test alert report generation"""
        alert_manager = AlertManager(server)
        
        # Generate some alerts
        with patch('psutil.Process.cpu_percent', return_value=95):
            alert_manager.check_alerts()
        
        # Generate alert report
        report = alert_manager.generate_report()
        
        # Verify report contents
        assert "alert_summary" in report
        assert "alert_history" in report
        assert "active_alerts" in report
        assert isinstance(report["alert_summary"], dict)
        assert isinstance(report["alert_history"], list)
        assert isinstance(report["active_alerts"], list)


"""Tests for monitoring functionality"""

import json
import socket
import time
from pathlib import Path

import pytest
import requests

from src.config.models import ServerConfig
from src.monitoring.metrics import MetricsManager
from src.server import StringSearchServer


@pytest.fixture
def metrics_url(server_config: ServerConfig) -> str:
    """Get metrics endpoint URL"""
    return f"http://{server_config.host}:{server_config.monitoring.prometheus_port}/metrics"


def test_metrics_server_start(metrics_manager: MetricsManager, metrics_url: str):
    """Test metrics server starts"""
    response = requests.get(metrics_url)
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_server_info_metric(
    server: StringSearchServer,
    metrics_url: str
):
    """Test server info metric"""
    response = requests.get(metrics_url)
    assert response.status_code == 200
    
    metrics = response.text
    assert 'server_info{version="' in metrics
    assert 'host="' + server.config.host in metrics
    assert 'port="' + str(server.config.port) in metrics


def test_active_connections_metric(
    server: StringSearchServer,
    metrics_url: str
):
    """Test active connections metric"""
    # Get initial connections
    response = requests.get(metrics_url)
    initial_metrics = response.text
    initial_connections = float([
        line.split()[1] for line in initial_metrics.split("\n")
        if line.startswith("active_connections")
    ][0])
    
    # Create new connection
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if server.config.security.ssl_enabled:
        ssl_wrapper = SSLWrapper(server.config.security)
        client = ssl_wrapper.wrap_socket(client, server_side=False)
    
    try:
        client.connect((server.config.host, server.config.port))
        
        # Check connections increased
        response = requests.get(metrics_url)
        current_metrics = response.text
        current_connections = float([
            line.split()[1] for line in current_metrics.split("\n")
            if line.startswith("active_connections")
        ][0])
        
        assert current_connections == initial_connections + 1
        
    finally:
        client.close()


def test_request_metrics(
    server: StringSearchServer,
    client: socket.socket,
    metrics_url: str
):
    """Test request metrics"""
    # Get initial metrics
    response = requests.get(metrics_url)
    initial_metrics = response.text
    initial_requests = float([
        line.split()[1] for line in initial_metrics.split("\n")
        if line.startswith("request_count_total")
    ][0])
    
    # Send search request
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    client.recv(4096)  # Get response
    
    # Check metrics updated
    response = requests.get(metrics_url)
    current_metrics = response.text
    current_requests = float([
        line.split()[1] for line in current_metrics.split("\n")
        if line.startswith("request_count_total")
    ][0])
    
    assert current_requests == initial_requests + 1
    assert "request_latency_seconds" in current_metrics
    assert "request_size_bytes" in current_metrics


def test_search_metrics(
    server: StringSearchServer,
    client: socket.socket,
    metrics_url: str
):
    """Test search metrics"""
    # Get initial metrics
    response = requests.get(metrics_url)
    initial_metrics = response.text
    initial_searches = float([
        line.split()[1] for line in initial_metrics.split("\n")
        if line.startswith("search_count_total")
    ][0])
    
    # Send search request
    request = {
        "pattern": "test",
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    data = json.dumps(request).encode() + b"\n"
    client.sendall(data)
    response = json.loads(client.recv(4096).decode())
    
    # Check metrics updated
    response = requests.get(metrics_url)
    current_metrics = response.text
    current_searches = float([
        line.split()[1] for line in current_metrics.split("\n")
        if line.startswith("search_count_total")
    ][0])
    
    assert current_searches == initial_searches + 1
    assert "search_latency_seconds" in current_metrics
    assert "search_results" in current_metrics


def test_error_metrics(
    server: StringSearchServer,
    client: socket.socket,
    metrics_url: str
):
    """Test error metrics"""
    # Get initial metrics
    response = requests.get(metrics_url)
    initial_metrics = response.text
    initial_errors = float([
        line.split()[1] for line in initial_metrics.split("\n")
        if line.startswith("error_count_total")
    ][0])
    
    # Send invalid request
    client.sendall(b"invalid json\n")
    client.recv(4096)  # Get error response
    
    # Check metrics updated
    response = requests.get(metrics_url)
    current_metrics = response.text
    current_errors = float([
        line.split()[1] for line in current_metrics.split("\n")
        if line.startswith("error_count_total")
    ][0])
    
    assert current_errors == initial_errors + 1


def test_resource_metrics(
    server: StringSearchServer,
    metrics_url: str
):
    """Test resource metrics"""
    response = requests.get(metrics_url)
    metrics = response.text
    
    assert "memory_usage_bytes" in metrics
    assert "cpu_usage_percent" in metrics
    assert "file_descriptors" in metrics
    assert "thread_count" in metrics


@pytest.mark.slow
def test_metrics_retention(
    server: StringSearchServer,
    metrics_url: str
):
    """Test metrics retention"""
    # Wait for metrics to be collected
    time.sleep(server.config.monitoring.metrics_retention + 0.1)
    
    # Check metrics still available
    response = requests.get(metrics_url)
    assert response.status_code == 200
    assert len(response.text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 