"""Tests for the configuration component"""

import os
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.config.models import (
    LogConfig,
    MonitoringConfig,
    ResourceConfig,
    SearchConfig,
    SecurityConfig,
    ServerConfig
)


def test_log_config():
    """Test log configuration validation"""
    # Valid config
    config = LogConfig(
        level="DEBUG",
        directory=Path("/tmp/logs")
    )
    assert config.level == "DEBUG"
    assert config.directory == Path("/tmp/logs")
    
    # Invalid log level
    with pytest.raises(ValidationError):
        LogConfig(level="INVALID", directory=Path("/tmp/logs"))


def test_monitoring_config():
    """Test monitoring configuration validation"""
    # Valid config
    config = MonitoringConfig(
        enabled=True,
        prometheus_port=9090
    )
    assert config.enabled
    assert config.prometheus_port == 9090
    
    # Invalid port
    with pytest.raises(ValidationError):
        MonitoringConfig(enabled=True, prometheus_port=-1)


def test_security_config(ssl_cert):
    """Test security configuration validation"""
    cert_file, key_file = ssl_cert
    
    # Valid config
    config = SecurityConfig(
        ssl_enabled=True,
        cert_file=cert_file,
        key_file=key_file,
        client_auth=False,
        allowed_ips=["127.0.0.1"],
        rate_limit=1000,
        rate_limit_burst=2000
    )
    assert config.ssl_enabled
    assert config.cert_file == cert_file
    assert config.key_file == key_file
    
    # Missing cert files when SSL enabled
    with pytest.raises(ValidationError):
        SecurityConfig(
            ssl_enabled=True,
            cert_file=Path("/nonexistent"),
            key_file=Path("/nonexistent"),
            client_auth=False,
            allowed_ips=["127.0.0.1"],
            rate_limit=1000,
            rate_limit_burst=2000
        )


def test_resource_config():
    """Test resource configuration validation"""
    # Valid config
    config = ResourceConfig(
        max_connections=100,
        connection_timeout=1.0,
        max_request_size=1024 * 1024,
        worker_threads=4,
        connection_pool_size=50,
        max_file_descriptors=1024
    )
    assert config.max_connections == 100
    assert config.connection_timeout == 1.0
    
    # Invalid values
    with pytest.raises(ValidationError):
        ResourceConfig(
            max_connections=-1,
            connection_timeout=1.0,
            max_request_size=1024 * 1024,
            worker_threads=4,
            connection_pool_size=50,
            max_file_descriptors=1024
        )


def test_search_config():
    """Test search configuration validation"""
    # Valid config
    config = SearchConfig(
        cache_size=1000,
        max_pattern_length=1000,
        default_case_sensitive=False,
        index_type="hash"
    )
    assert config.cache_size == 1000
    assert config.max_pattern_length == 1000
    
    # Invalid index type
    with pytest.raises(ValidationError):
        SearchConfig(
            cache_size=1000,
            max_pattern_length=1000,
            default_case_sensitive=False,
            index_type="invalid"
        )


def test_server_config(test_data_file: Path, ssl_cert):
    """Test server configuration validation"""
    cert_file, key_file = ssl_cert
    
    # Valid config
    config = ServerConfig(
        host="127.0.0.1",
        port=44445,
        data_file=test_data_file,
        log=LogConfig(
            level="DEBUG",
            directory=Path("/tmp/logs")
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
    assert config.host == "127.0.0.1"
    assert config.port == 44445
    assert config.data_file == test_data_file
    
    # Invalid port
    with pytest.raises(ValidationError):
        ServerConfig(
            host="127.0.0.1",
            port=-1,
            data_file=test_data_file,
            log=LogConfig(
                level="DEBUG",
                directory=Path("/tmp/logs")
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


def test_load_config_from_yaml(tmp_path: Path, test_data_file: Path, ssl_cert):
    """Test loading configuration from YAML file"""
    cert_file, key_file = ssl_cert
    
    # Create config file
    config_file = tmp_path / "config.yaml"
    config_data = {
        "host": "127.0.0.1",
        "port": 44445,
        "data_file": str(test_data_file),
        "log": {
            "level": "DEBUG",
            "directory": "/tmp/logs"
        },
        "monitoring": {
            "enabled": True,
            "prometheus_port": 9090
        },
        "security": {
            "ssl_enabled": True,
            "cert_file": str(cert_file),
            "key_file": str(key_file),
            "client_auth": False,
            "allowed_ips": ["127.0.0.1"],
            "rate_limit": 1000,
            "rate_limit_burst": 2000
        },
        "resources": {
            "max_connections": 100,
            "connection_timeout": 1.0,
            "max_request_size": 1024 * 1024,
            "worker_threads": 4,
            "connection_pool_size": 50,
            "max_file_descriptors": 1024
        },
        "search": {
            "cache_size": 1000,
            "max_pattern_length": 1000,
            "default_case_sensitive": False,
            "index_type": "hash"
        }
    }
    
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    # Load config
    config = ServerConfig.from_yaml(config_file)
    assert config.host == "127.0.0.1"
    assert config.port == 44445
    assert config.data_file == test_data_file
    assert config.log.level == "DEBUG"
    assert config.monitoring.enabled
    assert config.security.ssl_enabled
    assert config.resources.max_connections == 100
    assert config.search.cache_size == 1000 