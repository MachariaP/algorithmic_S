#!/usr/bin/env python3

"""
Error Handling Tests

This module tests error handling and recovery:
1. Network errors
2. File system errors
3. Memory errors
4. Configuration errors
5. Input validation
"""

import pytest
import socket
import threading
import tempfile
import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

from server import StringSearchServer


@pytest.fixture
def server() -> Generator[StringSearchServer, None, None]:
    """Fixture to create and start server for tests"""
    server = StringSearchServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    yield server
    server.sock.close()


class TestNetworkErrors:
    """Test network error handling"""

    def test_connection_reset(self, server: StringSearchServer) -> None:
        """Test handling of connection reset by peer"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            sock.recv(1024)
            # Force connection reset
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

        # Verify server still accepts new connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_partial_send(self, server: StringSearchServer) -> None:
        """Test handling of partial sends"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            # Send query in chunks
            query = b"test_string\n"
            for i in range(len(query)):
                sock.send(query[i:i+1])
                time.sleep(0.01)
            response = sock.recv(1024)
            assert response

    def test_invalid_request(self, server: StringSearchServer) -> None:
        """Test handling of invalid requests"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            # Send invalid data
            sock.send(b"\x00\xff\n")
            response = sock.recv(1024)
            assert b"error" in response.lower()


class TestFileSystemErrors:
    """Test file system error handling"""

    def test_missing_data_file(self, server: StringSearchServer) -> None:
        """Test handling of missing data file"""
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = temp_file.name
        
        server.config.file_path = temp_path
        with pytest.raises(FileNotFoundError):
            server.load_data()

    def test_permission_denied(self, server: StringSearchServer) -> None:
        """Test handling of permission denied"""
        with tempfile.NamedTemporaryFile() as temp_file:
            os.chmod(temp_file.name, 0o000)
            server.config.file_path = temp_file.name
            with pytest.raises(PermissionError):
                server.load_data()

    def test_file_corruption(self, server: StringSearchServer) -> None:
        """Test handling of corrupted data file"""
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            # Write some valid data
            temp_file.write("test1\ntest2\n")
            temp_file.flush()
            
            # Corrupt the file
            with open(temp_file.name, 'ab') as f:
                f.write(b'\x00\xff\x00\xff')
            
            server.config.file_path = temp_file.name
            with pytest.raises(UnicodeDecodeError):
                server.load_data()


class TestMemoryErrors:
    """Test memory error handling"""

    def test_out_of_memory(self, server: StringSearchServer) -> None:
        """Test handling of out of memory condition"""
        with patch('builtins.open') as mock_open:
            # Simulate large file
            mock_open.return_value.__enter__.return_value = (
                f"test_line_{i}\n" for i in range(10**7)
            )
            
            with pytest.raises(MemoryError):
                server.load_data()

    def test_memory_pressure(self, server: StringSearchServer) -> None:
        """Test handling of memory pressure"""
        original_size = len(server._data)
        
        # Add many items to create memory pressure
        large_data = ["x" * 1000000 for _ in range(1000)]
        
        try:
            for item in large_data:
                server._cached_search(item)
        except MemoryError:
            pass
        
        # Verify original data is preserved
        assert len(server._data) == original_size


class TestConfigurationErrors:
    """Test configuration error handling"""

    def test_invalid_port(self) -> None:
        """Test handling of invalid port"""
        server = StringSearchServer()
        server.config.port = -1
        with pytest.raises(ValueError):
            server.start()

    def test_invalid_host(self) -> None:
        """Test handling of invalid host"""
        server = StringSearchServer()
        server.config.host = "invalid_host"
        with pytest.raises(socket.gaierror):
            server.start()

    def test_port_in_use(self, server: StringSearchServer) -> None:
        """Test handling of port already in use"""
        # Try to start another server on same port
        new_server = StringSearchServer()
        with pytest.raises(OSError):
            new_server.start()


class TestInputValidation:
    """Test input validation"""

    def test_empty_query(self, server: StringSearchServer) -> None:
        """Test handling of empty query"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"\n")
            response = sock.recv(1024)
            assert b"error" in response.lower()

    def test_long_query(self, server: StringSearchServer) -> None:
        """Test handling of very long query"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"x" * 1000000 + b"\n")
            response = sock.recv(1024)
            assert b"error" in response.lower()

    def test_special_characters(self, server: StringSearchServer) -> None:
        """Test handling of special characters"""
        special_chars = [
            "\x00", "\xff", "\u0000", "\u2028", "\u2029",
            "\\", "'", '"', ";", "|", "&", "$", "`"
        ]
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            for char in special_chars:
                sock.send(f"test{char}string\n".encode())
                response = sock.recv(1024)
                assert response  # Server should handle or reject gracefully


class TestRecoveryBehavior:
    """Test recovery from error conditions"""

    def test_reconnect_after_error(self, server: StringSearchServer) -> None:
        """Test reconnection after connection error"""
        def simulate_error():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                sock.recv(1024)
                # Force error
                sock.shutdown(socket.SHUT_RDWR)

        # Simulate multiple connection errors
        for _ in range(10):
            simulate_error()
            time.sleep(0.1)

        # Verify server still accepts connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_reload_after_error(self, server: StringSearchServer) -> None:
        """Test data reload after error"""
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write("test1\ntest2\n")
            temp_file.flush()
            
            server.config.file_path = temp_file.name
            server.load_data()
            
            # Corrupt file and try to reload
            with open(temp_file.name, 'ab') as f:
                f.write(b'\x00\xff\x00\xff')
            
            with pytest.raises(UnicodeDecodeError):
                server.load_data()
            
            # Fix file and verify reload works
            with open(temp_file.name, 'w') as f:
                f.write("test1\ntest2\ntest3\n")
            
            server.load_data()
            assert server._cached_search("test3") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 