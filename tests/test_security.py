#!/usr/bin/env python3

"""
Security Tests

This module tests security features and protections:
1. SSL/TLS security
2. Input sanitization
3. Rate limiting
4. Resource limits
5. Access control
"""

import pytest
import socket
import ssl
import threading
import time
import tempfile
from pathlib import Path
from typing import Generator, Tuple
from unittest.mock import patch

from src.server import StringSearchServer
from src.ssl.cert_gen import generate_self_signed_cert


@pytest.fixture
def ssl_context() -> Generator[ssl.SSLContext, None, None]:
    """Fixture to create SSL context"""
    with tempfile.TemporaryDirectory() as temp_dir:
        cert_path = Path(temp_dir) / "server.crt"
        key_path = Path(temp_dir) / "server.key"
        
        # Generate self-signed certificate
        generate_self_signed_cert(
            cert_path=str(cert_path),
            key_path=str(key_path),
            country="US",
            state="CA",
            locality="Test City",
            organization="Test Org",
            organizational_unit="Test Unit",
            common_name="localhost"
        )
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        yield context


@pytest.fixture
def ssl_server(ssl_context: ssl.SSLContext) -> Generator[StringSearchServer, None, None]:
    """Fixture to create and start SSL-enabled server"""
    server = StringSearchServer()
    server.config.use_ssl = True
    server.ssl_context = ssl_context
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)  # Wait for server to start
    yield server
    server.sock.close()


class TestSSLSecurity:
    """Test SSL/TLS security features"""

    def test_ssl_connection(self, ssl_server: StringSearchServer) -> None:
        """Test basic SSL connection"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection(('localhost', 44445)) as sock:
            with context.wrap_socket(sock, server_hostname='localhost') as ssl_sock:
                ssl_sock.send(b"test\n")
                assert ssl_sock.recv(1024)

    def test_protocol_versions(self, ssl_server: StringSearchServer) -> None:
        """Test supported SSL/TLS protocol versions"""
        # Test TLS 1.2
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection(('localhost', 44445)) as sock:
            with context.wrap_socket(sock) as ssl_sock:
                ssl_sock.send(b"test\n")
                assert ssl_sock.recv(1024)

        # Test TLS 1.3
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection(('localhost', 44445)) as sock:
            with context.wrap_socket(sock) as ssl_sock:
                ssl_sock.send(b"test\n")
                assert ssl_sock.recv(1024)

    def test_cipher_suites(self, ssl_server: StringSearchServer) -> None:
        """Test supported cipher suites"""
        context = ssl.create_default_context()
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection(('localhost', 44445)) as sock:
            with context.wrap_socket(sock, server_hostname='localhost') as ssl_sock:
                cipher = ssl_sock.cipher()
                assert cipher[0] in [
                    'TLS_AES_256_GCM_SHA384',
                    'TLS_CHACHA20_POLY1305_SHA256',
                    'TLS_AES_128_GCM_SHA256'
                ]


class TestInputSanitization:
    """Test input sanitization"""

    def test_sql_injection(self, server: StringSearchServer) -> None:
        """Test SQL injection prevention"""
        injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
            "' OR 1=1; --"
        ]
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
        for attempt in injection_attempts:
                sock.send(f"{attempt}\n".encode())
                response = sock.recv(1024)
                assert b"error" in response.lower() or b"false" in response.lower()

    def test_command_injection(self, server: StringSearchServer) -> None:
        """Test command injection prevention"""
        injection_attempts = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(id)",
            "&& echo hacked"
        ]
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
        for attempt in injection_attempts:
                sock.send(f"{attempt}\n".encode())
                response = sock.recv(1024)
                assert b"error" in response.lower() or b"false" in response.lower()

    def test_path_traversal(self, server: StringSearchServer) -> None:
        """Test path traversal prevention"""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\Windows\\System32\\config\\SAM",
            "/etc/shadow",
            "C:\\Windows\\win.ini"
        ]
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            for attempt in traversal_attempts:
                sock.send(f"{attempt}\n".encode())
                response = sock.recv(1024)
                assert b"error" in response.lower() or b"false" in response.lower()


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_per_ip_rate_limit(self, server: StringSearchServer) -> None:
        """Test per-IP rate limiting"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Send requests rapidly
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < 1:
                try:
                    sock.send(b"test\n")
                    sock.recv(1024)
                    request_count += 1
                except socket.error:
                    break
            
            assert request_count <= server.config.rate_limit

    def test_burst_handling(self, server: StringSearchServer) -> None:
        """Test burst request handling"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Send burst of requests
            for _ in range(100):
                sock.send(b"test\n")
            
            # Verify responses
            for _ in range(100):
                response = sock.recv(1024)
                assert response

    def test_rate_limit_reset(self, server: StringSearchServer) -> None:
        """Test rate limit reset after window expiration"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Exhaust rate limit
            for _ in range(server.config.rate_limit):
                    sock.send(b"test\n")
                    sock.recv(1024)

            # Wait for rate limit window to reset
            time.sleep(server.config.rate_limit_window)
            
            # Verify can make requests again
            sock.send(b"test\n")
            assert sock.recv(1024)


class TestResourceLimits:
    """Test resource limit enforcement"""

    def test_max_connections(self, server: StringSearchServer) -> None:
        """Test maximum connection limit"""
        sockets = []
        try:
            for _ in range(server.config.max_connections + 1):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                sockets.append(sock)
        except socket.error:
            pass
        finally:
            for sock in sockets:
                sock.close()

        assert len(sockets) <= server.config.max_connections

    def test_request_size_limit(self, server: StringSearchServer) -> None:
        """Test request size limit"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Send oversized request
            sock.send(b"x" * (server.config.max_request_size + 1) + b"\n")
            response = sock.recv(1024)
            assert b"error" in response.lower()

    def test_response_size_limit(self, server: StringSearchServer) -> None:
        """Test response size limit"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Generate query that would produce large response
            sock.send(b"." * 1000 + b"\n")  # Regex pattern matching many lines
            response = sock.recv(server.config.max_response_size + 1024)
            assert len(response) <= server.config.max_response_size


class TestAccessControl:
    """Test access control features"""

    def test_ip_whitelist(self, server: StringSearchServer) -> None:
        """Test IP whitelist functionality"""
        with patch.object(server.config, 'ip_whitelist', ['127.0.0.1']):
            # Test allowed IP
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                assert sock.recv(1024)

            # Test blocked IP
            with patch('socket.socket.getpeername', return_value=('1.2.3.4', 12345)):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    with pytest.raises(ConnectionRefusedError):
                        sock.connect(('localhost', 44445))

    def test_ip_blacklist(self, server: StringSearchServer) -> None:
        """Test IP blacklist functionality"""
        with patch.object(server.config, 'ip_blacklist', ['1.2.3.4']):
            # Test allowed IP
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                assert sock.recv(1024)

            # Test blocked IP
            with patch('socket.socket.getpeername', return_value=('1.2.3.4', 12345)):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    with pytest.raises(ConnectionRefusedError):
                        sock.connect(('localhost', 44445))


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 