#!/usr/bin/env python3

"""
Reliability Tests

This module tests system reliability:
1. Fault tolerance
2. Data consistency
3. Recovery behavior
4. Error handling
5. System stability
"""

import pytest
import socket
import threading
import time
import random
import tempfile
import os
import signal
import psutil
from pathlib import Path
from typing import Generator, List, Dict, Set
from concurrent.futures import ThreadPoolExecutor

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


@pytest.fixture
def test_data_file() -> Generator[Path, None, None]:
    """Fixture to create test data file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        # Write test data
        for i in range(10000):
            temp_file.write(f"test_line_{i}\n")
        temp_file.flush()
        yield Path(temp_file.name)
        os.unlink(temp_file.name)


class TestFaultTolerance:
    """Test fault tolerance capabilities"""

    def test_connection_failures(self, server: StringSearchServer) -> None:
        """Test handling of connection failures"""
        def error_connection() -> None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                # Send partial data and close abruptly
                sock.send(b"test")
                sock.close()
            except Exception:
                pass

        # Create many error connections
        threads = []
        for _ in range(1000):
            thread = threading.Thread(target=error_connection)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Verify server still functions
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_network_errors(self, server: StringSearchServer) -> None:
        """Test handling of network errors"""
        def simulate_network_error() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                # Set very short timeout
                sock.settimeout(0.001)
                try:
                    sock.send(b"test\n")
                    sock.recv(1024)
                except socket.timeout:
                    pass

        # Run multiple error simulations
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=simulate_network_error)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Verify server still works
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_resource_exhaustion(self, server: StringSearchServer) -> None:
        """Test handling of resource exhaustion"""
        # Try to exhaust file descriptors
        sockets = []
        try:
            while True:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                sockets.append(sock)
        except (socket.error, OSError):
            pass

        # Verify server recovers
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

        # Cleanup
        for sock in sockets:
            try:
                sock.close()
            except Exception:
                pass


class TestDataConsistency:
    """Test data consistency guarantees"""

    def test_concurrent_access(self, server: StringSearchServer, test_data_file: Path) -> None:
        """Test data consistency under concurrent access"""
        server.config.file_path = test_data_file
        server.load_data()

        def client_session(results: List[bool]) -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(100):
                    sock.send(b"test_line_0\n")
                    response = sock.recv(1024)
                    results.append(b"true" in response.lower())

        # Run concurrent clients
        results: List[bool] = []
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=client_session, args=(results,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Verify all results are consistent
        assert all(results), "Inconsistent search results"

    def test_data_reload(self, server: StringSearchServer, test_data_file: Path) -> None:
        """Test consistency during data reloads"""
        server.config.file_path = test_data_file
        server.load_data()

        def client_worker(results: List[Dict[str, Any]]) -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(100):
                    start = time.perf_counter()
                    sock.send(b"test_line_0\n")
                    response = sock.recv(1024)
                    duration = time.perf_counter() - start
                    results.append({
                        'success': b"true" in response.lower(),
                        'time': duration
                    })

        # Start client threads
        results: List[Dict[str, Any]] = []
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=client_worker, args=(results,))
            thread.start()
            threads.append(thread)

        # Reload data while clients are running
        time.sleep(0.5)
        server.load_data()

        for thread in threads:
            thread.join()

        # Verify consistency and performance
        assert all(r['success'] for r in results), "Inconsistent results during reload"
        avg_time = sum(r['time'] for r in results) / len(results)
        assert avg_time < 0.01, f"High latency during reload: {avg_time*1000:.2f}ms"

    def test_cache_consistency(self, server: StringSearchServer, test_data_file: Path) -> None:
        """Test cache consistency"""
        server.config.file_path = test_data_file
        server.load_data()

        # Perform initial searches to populate cache
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            for i in range(100):
                sock.send(f"test_line_{i}\n".encode())
                sock.recv(1024)

        # Modify data file
        with open(test_data_file, 'a') as f:
            f.write("new_test_line\n")

        # Reload data
        server.load_data()

        # Verify cache is consistent with new data
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"new_test_line\n")
            response = sock.recv(1024)
            assert b"true" in response.lower()


class TestRecoveryBehavior:
    """Test system recovery capabilities"""

    def test_crash_recovery(self, server: StringSearchServer, test_data_file: Path) -> None:
        """Test recovery from crashes"""
        server.config.file_path = test_data_file
        server.load_data()

        def crash_server() -> None:
            # Simulate crash by forcefully terminating the process
            os.kill(os.getpid(), signal.SIGTERM)

        # Start recovery monitor
        def recovery_monitor() -> None:
            time.sleep(1)  # Wait for crash
            # Start new server
            new_server = StringSearchServer()
            new_server.config.file_path = test_data_file
            new_server_thread = threading.Thread(target=new_server.start)
            new_server_thread.daemon = True
            new_server_thread.start()

        # Start monitor thread
        monitor_thread = threading.Thread(target=recovery_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()

        try:
            crash_server()
        except SystemExit:
            pass

        # Verify new server works
        time.sleep(2)  # Wait for recovery
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test_line_0\n")
            assert sock.recv(1024)

    def test_data_corruption_recovery(self, server: StringSearchServer) -> None:
        """Test recovery from data corruption"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            # Write valid data
            temp_file.write("test_line_1\n")
            temp_file.write("test_line_2\n")
            temp_file.flush()
            
            server.config.file_path = Path(temp_file.name)
            server.load_data()

            # Corrupt the file
            with open(temp_file.name, 'ab') as f:
                f.write(b'\x00\xff\x00\xff')

            # Attempt reload
            try:
                server.load_data()
            except Exception:
                # Restore valid data
                with open(temp_file.name, 'w') as f:
                    f.write("test_line_1\n")
                    f.write("test_line_2\n")
                server.load_data()

            # Verify recovery
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test_line_1\n")
                assert sock.recv(1024)

            os.unlink(temp_file.name)

    def test_partial_failure_recovery(self, server: StringSearchServer) -> None:
        """Test recovery from partial failures"""
        def simulate_partial_failure() -> None:
            # Simulate partial system failure
            process = psutil.Process()
            
            # Consume memory
            data = []
            try:
                while True:
                    data.append(b"x" * 1000000)
            except MemoryError:
                pass

            # Release memory
            del data

            # Consume CPU
            end_time = time.time() + 1
            while time.time() < end_time:
                _ = sum(i * i for i in range(10000))

            # Consume file descriptors
            fds = []
            try:
                while True:
                    fds.append(open(os.devnull))
            except OSError:
                pass
            finally:
                for fd in fds:
                    fd.close()

        # Run partial failure simulation
        simulate_partial_failure()

        # Verify server recovers
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)


class TestErrorHandling:
    """Test error handling capabilities"""

    def test_invalid_requests(self, server: StringSearchServer) -> None:
        """Test handling of invalid requests"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            invalid_requests = [
                b"",  # Empty request
                b"\x00\xff",  # Binary data
                b"test" * 1000000,  # Very large request
                b"test\ntest",  # Multiple lines
                b"test\0",  # Null byte
            ]
            
            for request in invalid_requests:
                sock.send(request)
                response = sock.recv(1024)
                assert b"error" in response.lower()

    def test_protocol_errors(self, server: StringSearchServer) -> None:
        """Test handling of protocol errors"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Test invalid protocol sequences
            sock.send(b"test")  # Missing newline
            time.sleep(0.1)
            sock.send(b"\n")  # Delayed newline
            assert sock.recv(1024)
            
            sock.send(b"test\ntest\n")  # Multiple requests
            assert sock.recv(1024)
            
            sock.send(b"test")  # Incomplete request
            sock.close()

    def test_resource_limits(self, server: StringSearchServer) -> None:
        """Test handling of resource limits"""
        # Test connection limit
        sockets = []
        try:
            for _ in range(10000):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                sockets.append(sock)
        except socket.error:
            pass

        # Test memory limit
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"x" * 1000000 + b"\n")  # Large request
            response = sock.recv(1024)
            assert b"error" in response.lower()

        # Cleanup
        for sock in sockets:
            try:
                sock.close()
            except Exception:
                pass


class TestSystemStability:
    """Test system stability"""

    def test_long_term_stability(self, server: StringSearchServer) -> None:
        """Test long-term system stability"""
        def client_worker() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                end_time = time.time() + 300  # 5 minutes
                while time.time() < end_time:
                    sock.send(b"test\n")
                    assert sock.recv(1024)
                    time.sleep(0.1)

        # Start client threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=client_worker)
            thread.start()
            threads.append(thread)

        # Monitor system resources
        process = psutil.Process()
        start_time = time.time()
        resource_samples = []

        while any(t.is_alive() for t in threads):
            resource_samples.append({
                'memory': process.memory_info().rss,
                'cpu': process.cpu_percent(),
                'threads': process.num_threads(),
                'fds': len(process.open_files()),
                'time': time.time() - start_time
            })
            time.sleep(1)

        # Wait for completion
        for thread in threads:
            thread.join()

        # Analyze stability
        memory_growth = resource_samples[-1]['memory'] - resource_samples[0]['memory']
        max_cpu = max(s['cpu'] for s in resource_samples)
        max_threads = max(s['threads'] for s in resource_samples)
        max_fds = max(s['fds'] for s in resource_samples)

        # Verify stability metrics
        assert memory_growth < 100 * 1024 * 1024, f"Memory leak detected: {memory_growth/1024/1024:.1f}MB"
        assert max_cpu < 80, f"High CPU usage: {max_cpu:.1f}%"
        assert max_threads < 100, f"Too many threads: {max_threads}"
        assert max_fds < 1000, f"Too many file descriptors: {max_fds}"

    def test_load_variation(self, server: StringSearchServer) -> None:
        """Test stability under varying load"""
        def generate_load(pattern: str) -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                end_time = time.time() + 60
                while time.time() < end_time:
                    if pattern == "burst":
                        # Send burst of requests
                        for _ in range(100):
                            sock.send(b"test\n")
                            sock.recv(1024)
                        time.sleep(1)
                    elif pattern == "steady":
                        # Send steady stream
                        sock.send(b"test\n")
                        sock.recv(1024)
                        time.sleep(0.01)
                    else:  # random
                        # Send random pattern
                        if random.random() < 0.5:
                            sock.send(b"test\n")
                            sock.recv(1024)
                        time.sleep(random.uniform(0, 0.1))

        # Start different load patterns
        patterns = ["burst", "steady", "random"]
        threads = []
        for pattern in patterns:
            for _ in range(3):
                thread = threading.Thread(target=generate_load, args=(pattern,))
                thread.start()
                threads.append(thread)

        # Monitor stability
        process = psutil.Process()
        while any(t.is_alive() for t in threads):
            cpu_percent = process.cpu_percent()
            memory_usage = process.memory_info().rss
            
            # Verify stability
            assert cpu_percent < 80, f"CPU usage too high: {cpu_percent:.1f}%"
            assert memory_usage < 1024 * 1024 * 1024, f"Memory usage too high: {memory_usage/1024/1024:.1f}MB"
            
            time.sleep(1)

        for thread in threads:
            thread.join()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 