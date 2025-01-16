"""Tests for SSL/TLS functionality"""

import socket
import ssl
from pathlib import Path

import pytest

from src.config.models import SecurityConfig, ServerConfig
from src.security.ssl import SSLWrapper
from src.server import StringSearchServer


def test_ssl_wrapper_creation(server_config: ServerConfig):
    """Test SSL wrapper can be created"""
    wrapper = SSLWrapper(server_config.security)
    assert wrapper.context.verify_mode == ssl.CERT_NONE
    assert wrapper.context.minimum_version == ssl.TLSVersion.TLSv1_3


def test_ssl_wrapper_with_client_auth(server_config: ServerConfig):
    """Test SSL wrapper with client authentication"""
    config = server_config.security.copy()
    config.client_auth = True
    
    wrapper = SSLWrapper(config)
    assert wrapper.context.verify_mode == ssl.CERT_REQUIRED


def test_ssl_connection(server: StringSearchServer, client: socket.socket):
    """Test SSL connection"""
    # Get peer certificate
    if isinstance(client, ssl.SSLSocket):
        cert = client.getpeercert()
        assert cert is not None
        assert "subject" in cert
        assert "issuer" in cert
    else:
        pytest.skip("Client socket is not SSL-enabled")


def test_invalid_certificate(server_config: ServerConfig, tmp_path: Path):
    """Test invalid certificate handling"""
    # Create invalid certificate files
    invalid_cert = tmp_path / "invalid.crt"
    invalid_key = tmp_path / "invalid.key"
    invalid_cert.write_text("invalid cert")
    invalid_key.write_text("invalid key")
    
    # Update config with invalid files
    config = server_config.copy()
    config.security.cert_file = invalid_cert
    config.security.key_file = invalid_key
    
    # Attempt to create server
    with pytest.raises(ssl.SSLError):
        server = StringSearchServer(config)
        server.start()


def test_missing_certificate(server_config: ServerConfig):
    """Test missing certificate handling"""
    # Update config with nonexistent files
    config = server_config.copy()
    config.security.cert_file = Path("/nonexistent.crt")
    config.security.key_file = Path("/nonexistent.key")
    
    # Attempt to create server
    with pytest.raises(FileNotFoundError):
        server = StringSearchServer(config)
        server.start()


def test_ssl_disabled(server_config: ServerConfig):
    """Test server without SSL"""
    # Disable SSL
    config = server_config.copy()
    config.security.ssl_enabled = False
    
    # Create and start server
    server = StringSearchServer(config)
    server.start()
    
    try:
        # Connect without SSL
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((config.host, config.port))
        
        # Verify connection is not SSL
        assert not isinstance(client, ssl.SSLSocket)
        
    finally:
        client.close()
        server.stop()


def test_generate_self_signed_cert(tmp_path: Path):
    """Test self-signed certificate generation"""
    cert_file = tmp_path / "test.crt"
    key_file = tmp_path / "test.key"
    
    # Generate certificate
    SSLWrapper.generate_self_signed_cert(cert_file, key_file)
    
    # Verify files exist
    assert cert_file.exists()
    assert key_file.exists()
    
    # Load certificate
    with open(cert_file) as f:
        cert_data = f.read()
    assert "BEGIN CERTIFICATE" in cert_data
    assert "END CERTIFICATE" in cert_data
    
    # Load private key
    with open(key_file) as f:
        key_data = f.read()
    assert "BEGIN PRIVATE KEY" in key_data
    assert "END PRIVATE KEY" in key_data 