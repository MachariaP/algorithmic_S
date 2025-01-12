#!/usr/bin/env python3

"""Shared test fixtures"""

import pytest
import tempfile
import socket
import os
import ssl
from pathlib import Path
from typing import Generator, Any, Tuple
from src.config.config import Config
from src.ssl.cert_gen import generate_self_signed_cert

@pytest.fixture
def ssl_certs(tmp_path) -> Tuple[Path, Path]:
    """Generate SSL certificates for testing"""
    cert_dir = tmp_path / "ssl"
    cert_dir.mkdir()
    return generate_self_signed_cert(cert_dir)

@pytest.fixture
def ssl_config(test_config, ssl_certs) -> Config:
    """Create SSL-enabled config"""
    key_path, cert_path = ssl_certs
    test_config.ssl_enabled = True
    test_config.ssl_cert_path = str(cert_path)
    test_config.ssl_key_path = str(key_path)
    return test_config

@pytest.fixture
def test_data_file() -> Generator[Path, Any, None]:
    """Create temporary test data file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        test_strings = [
            "7;0;6;28;0;23;5;0;",
            "1;0;6;16;0;19;3;0;",
            "18;0;21;26;0;17;3;0;",
            "20;0;1;11;0;12;5;0;"
        ]
        for string in test_strings:
            f.write(f"{string}\n")
            
    yield Path(f.name)
    Path(f.name).unlink()

@pytest.fixture
def test_config(tmp_path) -> Config:
    """Create test configuration
    
    Args:
        tmp_path: Temporary directory path
        
    Returns:
        Test configuration
    """
    # Create test data file
    data_file = tmp_path / "test.txt"
    with open(data_file, 'w') as f:
        f.write("test_string\n")
    
    config = Config()
    config.file_path = str(data_file)
    config.reread_on_query = False
    config.ssl_enabled = False
    config.rate_limit_enabled = False
    return config

@pytest.fixture
def server_port() -> int:
    """Get available port"""
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1] 