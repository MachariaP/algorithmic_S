#!/usr/bin/env python3

"""
Edge Case Tests

This module contains specific test cases for:
1. Input validation and boundary conditions
2. File handling edge cases
3. Network protocol edge cases
4. Concurrency edge cases
5. Resource limit scenarios
"""

import pytest
import socket
import ssl
import time
import threading
import signal
from pathlib import Path
from typing import Generator

from server import StringSearchServer


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


class TestInputValidation:
    """Test input validation edge cases"""

    def test_null_bytes(self, server: StringSearchServer) -> None:
        """Test strings containing null bytes"""
        test_cases = [
            "test\x00string",
            "\x00test",
            "test\x00",
            "\x00\x00\x00"
        ]
        for test in test_cases:
            assert server._cached_search(test) is False

    def test_control_characters(self, server: StringSearchServer) -> None:
        """Test strings with control characters"""
        control_chars = [chr(i) for i in range(32)]  # ASCII control chars
        for char in control_chars:
            assert server._cached_search(f"test{char}string") is False

    def test_line_endings(self, server: StringSearchServer) -> None:
        """Test different line ending combinations"""
        test_cases = [
            "test\n",
            "test\r",
            "test\r\n",
            "test\n\r",
            "\ntest",
            "\rtest",
            "\r\ntest"
        ]
        for test in test_cases:
            assert server._cached_search(test) is False

    def test_whitespace(self, server: StringSearchServer) -> None:
        """Test whitespace handling"""
        whitespace = [
            " test ",          # Leading/trailing spaces
            "\ttest\t",        # Tabs
            " \t test \t ",    # Mixed whitespace
            "test  test",      # Multiple spaces
            "\u2000test",      # Unicode whitespace
            "\u205Ftest"       # Mathematical space
        ]
        for test in whitespace:
            assert server._cached_search(test) is False


class TestFileHandling:
    """Test file handling edge cases"""

    def test_empty_file(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test handling of empty file"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        server.config.file_path = empty_file
        server.load_data()
        assert len(server.data) == 0

    def test_single_character_lines(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test handling of single-character lines"""
        test_file = tmp_path / "single_chars.txt"
        test_file.write_text("a\nb\nc\n")
        server.config.file_path = test_file
        server.load_data()
        assert server._cached_search("b") is True

    def test_identical_lines(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test handling of identical lines"""
        test_file = tmp_path / "identical.txt"
        test_file.write_text("test\ntest\ntest\n")
        server.config.file_path = test_file
        server.load_data()
        assert len(server.data) == 1  # Should deduplicate

    def test_file_permissions(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test handling of permission-restricted files"""
        test_file = tmp_path / "restricted.txt"
        test_file.write_text("test")
        test_file.chmod(0o000)  # Remove all permissions
        with pytest.raises(PermissionError):
            server.config.file_path = test_file
            server.load_data()


class TestNetworkProtocol:
    """Test network protocol edge cases"""

    def test_partial_sends(self, server: StringSearchServer) -> None:
        """Test handling of partial sends"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            # Send string byte by byte
            test_string = b"test_string\n"
            for byte in test_string:
                sock.send(bytes([byte]))
                time.sleep(0.01)
            response = sock.recv(1024)
            assert b"STRING NOT FOUND" in response

    def test_connection_reset(self, server: StringSearchServer) -> None:
        """Test handling of connection reset"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test")
            # Force connection reset
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

    def test_slow_client(self, server: StringSearchServer) -> None:
        """Test handling of slow clients"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            time.sleep(1)  # Simulate slow client
            sock.send(b"test_string\n")
            response = sock.recv(1024)
            assert b"STRING NOT FOUND" in response

    def test_large_payload(self, server: StringSearchServer) -> None:
        """Test handling of large payloads"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            # Send payload larger than buffer size
            sock.send(b"x" * 2048)
            response = sock.recv(1024)
            assert b"ERROR" in response


class TestConcurrencyScenarios:
    """Test concurrency edge cases"""

    def test_rapid_connect_disconnect(self, server: StringSearchServer) -> None:
        """Test rapid connection/disconnection"""
        for _ in range(1000):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 44445))
            sock.close()

    def test_simultaneous_ssl_handshakes(self, server: StringSearchServer) -> None:
        """Test simultaneous SSL handshakes"""
        server.config.ssl_enabled = True
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        def ssl_connect():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                with context.wrap_socket(sock) as ssock:
                    ssock.connect(('localhost', 44445))
                    ssock.send(b"test\n")
                    ssock.recv(1024)

        threads = [threading.Thread(target=ssl_connect) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_mixed_protocol_clients(self, server: StringSearchServer) -> None:
        """Test mixing SSL and non-SSL clients"""
        server.config.ssl_enabled = True
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        def ssl_client():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                with context.wrap_socket(sock) as ssock:
                    ssock.connect(('localhost', 44445))
                    ssock.send(b"test\n")
                    ssock.recv(1024)

        def plain_client():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                sock.recv(1024)

        threads = ([threading.Thread(target=ssl_client) for _ in range(50)] +
                  [threading.Thread(target=plain_client) for _ in range(50)])
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class TestResourceLimits:
    """Test resource limit scenarios"""

    def test_memory_pressure(self, server: StringSearchServer) -> None:
        """Test behavior under memory pressure"""
        large_data = ["x" * 1000000 for _ in range(1000)]  # Allocate ~1GB
        try:
            for data in large_data:
                server._cached_search(data)
        except MemoryError:
            pass  # Expected
        # Verify server still functions
        assert server._cached_search("test") is False

    def test_file_descriptor_exhaustion(self, server: StringSearchServer) -> None:
        """Test handling of file descriptor exhaustion"""
        open_files = []
        try:
            while True:
                open_files.append(open("/dev/null"))
        except OSError:
            pass  # Expected
        finally:
            for f in open_files:
                f.close()
        # Verify server still functions
        assert server._cached_search("test") is False

    def test_cpu_intensive_load(self, server: StringSearchServer) -> None:
        """Test behavior under CPU load"""
        def cpu_load():
            while True:
                _ = [i * i for i in range(10000)]

        load_thread = threading.Thread(target=cpu_load)
        load_thread.daemon = True
        load_thread.start()

        start = time.perf_counter()
        server._cached_search("test")
        duration = time.perf_counter() - start
        assert duration < 1.0, "Search too slow under CPU load"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
