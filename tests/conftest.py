#!/usr/bin/env python3

"""Test fixtures and configuration"""

import asyncio
import logging
import os
import socket
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional

import pytest
import pytest_asyncio
from _pytest.logging import LogCaptureFixture

from src.config.models import ServerConfig
from src.monitoring.metrics import MetricsManager
from src.security.ssl import SSLWrapper
from src.server import StringSearchServer
from src.utils.logging import setup_logging


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def test_data_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Create test data file"""
    data_file = temp_dir / "test_data.txt"
    with open(data_file, "w") as f:
        f.write("\n".join([
            "test line 1",
            "test line 2",
            "another test line",
            "final test line"
        ]))
    yield data_file


@pytest.fixture(scope="session")
def ssl_cert(temp_dir: Path) -> Generator[tuple[Path, Path], None, None]:
    """Generate SSL certificate for testing"""
    cert_file = temp_dir / "test.crt"
    key_file = temp_dir / "test.key"
    SSLWrapper.generate_self_signed_cert(cert_file, key_file)
    yield cert_file, key_file


@pytest.fixture
def server_config(
    temp_dir: Path,
    test_data_file: Path,
    ssl_cert: tuple[Path, Path]
) -> ServerConfig:
    """Create server configuration for testing"""
    cert_file, key_file = ssl_cert
    return ServerConfig(
        host="127.0.0.1",
        port=44445,
        data_file=test_data_file,
        log=LogConfig(
            level="DEBUG",
            directory=temp_dir / "logs"
        ),
        monitoring=MonitoringConfig(
            enabled=True,
            prometheus_port=9090
        ),
        security=SecurityConfig(
            ssl_enabled=True,
            cert_file=cert_file,
            key_file=key_file,
            client_auth=False,
            allowed_ips=["127.0.0.1"],
            rate_limit=1000,
            rate_limit_burst=2000
        ),
        resources=ResourceConfig(
            max_connections=100,
            connection_timeout=1.0,
            max_request_size=1024 * 1024,
            worker_threads=4,
            connection_pool_size=50,
            max_file_descriptors=1024
        ),
        search=SearchConfig(
            cache_size=1000,
            max_pattern_length=1000,
            default_case_sensitive=False,
            index_type="hash"
        )
    )


@pytest.fixture
def metrics_manager() -> Generator[MetricsManager, None, None]:
    """Create metrics manager for testing"""
    manager = MetricsManager(port=9090)
    manager.start()
    yield manager


@pytest.fixture
def server(
    server_config: ServerConfig,
    metrics_manager: MetricsManager,
    caplog: LogCaptureFixture
) -> Generator[StringSearchServer, None, None]:
    """Create and start server for testing"""
    caplog.set_level(logging.DEBUG)
    
    server = StringSearchServer(server_config)
    server.start()
    yield server
    server.stop()


@pytest_asyncio.fixture
async def client(
    server: StringSearchServer,
    server_config: ServerConfig
) -> AsyncGenerator[socket.socket, None]:
    """Create client socket for testing"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    if server_config.security.ssl_enabled:
        ssl_wrapper = SSLWrapper(server_config.security)
        sock = ssl_wrapper.wrap_socket(sock, server_side=False)
        
    await asyncio.get_event_loop().sock_connect(
        sock,
        (server_config.host, server_config.port)
    )
    
    yield sock
    
    sock.close()


@pytest.fixture
def mock_notifier():
    """Create mock notifier for testing alerts"""
    class MockNotifier:
        def __init__(self):
            self.notifications = []
            
        def send_notification(self, alert):
            self.notifications.append(alert)
            
    return MockNotifier()


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
                
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom options"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests"
    )
