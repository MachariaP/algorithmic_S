#!/usr/bin/env python3

"""
Stress Tests

This module tests server behavior under stress:
1. High concurrency
2. Large data sets
3. Resource exhaustion
4. Long-running operations
5. Error conditions
"""

import pytest
import socket
import threading
import time
import random
import string
import tempfile
import os
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
def large_data_file() -> Generator[Path, None, None]:
    """Fixture to create large test data file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        # Generate large dataset
        for i in range(1000000):  # 1 million lines
            line = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            temp_file.write(f"{line}\n")
        temp_file.flush()
        yield Path(temp_file.name)
        os.unlink(temp_file.name)


class TestHighConcurrency:
    """Test high concurrency scenarios"""

    def test_concurrent_connections(self, server: StringSearchServer) -> None:
        """Test many concurrent connections"""
        def client_session() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(100):
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Create many concurrent clients
        num_clients = 1000
        threads = []
        for _ in range(num_clients):
            thread = threading.Thread(target=client_session)
            thread.start()
            threads.append(thread)

        # Wait for all clients to finish
        for thread in threads:
            thread.join()

    def test_connection_flood(self, server: StringSearchServer) -> None:
        """Test rapid connection/disconnection"""
        def connection_cycle() -> None:
            for _ in range(100):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect(('localhost', 44445))
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Run multiple connection cycles concurrently
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(connection_cycle) for _ in range(50)]
            for future in futures:
                future.result()

    def test_parallel_searches(self, server: StringSearchServer) -> None:
        """Test parallel search operations"""
        def search_worker(queries: List[str]) -> Dict[str, bool]:
            results = {}
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for query in queries:
                    sock.send(f"{query}\n".encode())
                    response = sock.recv(1024)
                    results[query] = b"true" in response.lower()
            return results

        # Generate random queries
        queries = [
            ''.join(random.choices(string.ascii_letters, k=10))
            for _ in range(1000)
        ]

        # Split queries among workers
        num_workers = 50
        queries_per_worker = len(queries) // num_workers
        worker_queries = [
            queries[i:i + queries_per_worker]
            for i in range(0, len(queries), queries_per_worker)
        ]

        # Run parallel searches
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(search_worker, worker_queries[i])
                for i in range(num_workers)
            ]
            results = [future.result() for future in futures]

        # Verify all searches completed
        all_results = {}
        for result_dict in results:
            all_results.update(result_dict)
        assert len(all_results) == len(queries)


class TestLargeDataSets:
    """Test handling of large data sets"""

    def test_large_file_load(self, server: StringSearchServer, large_data_file: Path) -> None:
        """Test loading large data file"""
        start_time = time.time()
        server.config.file_path = large_data_file
        server.load_data()
        load_time = time.time() - start_time
        
        # Verify load time is reasonable
        assert load_time < 60, f"Load time too high: {load_time:.2f}s"

        # Verify search still works
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_large_searches(self, server: StringSearchServer, large_data_file: Path) -> None:
        """Test searching in large dataset"""
        server.config.file_path = large_data_file
        server.load_data()

        def measure_search_time(query: str) -> float:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                start = time.perf_counter()
                sock.send(f"{query}\n".encode())
                sock.recv(1024)
                return time.perf_counter() - start

        # Test different query patterns
        patterns = [
            "^specific",  # Start of line
            "middle.*pattern",  # Middle pattern
            "end$",  # End of line
            ".*",  # Match everything
            "[a-z]+",  # Character class
            "rare.*pattern"  # Rare pattern
        ]

        # Measure search times
        search_times = {
            pattern: measure_search_time(pattern)
            for pattern in patterns
        }

        # Verify search times are reasonable
        for pattern, duration in search_times.items():
            assert duration < 1.0, f"Search too slow for pattern '{pattern}': {duration:.2f}s"

    def test_memory_efficiency(self, server: StringSearchServer, large_data_file: Path) -> None:
        """Test memory efficiency with large dataset"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Load large dataset
        server.config.file_path = large_data_file
        server.load_data()

        # Measure memory usage
        final_memory = process.memory_info().rss
        memory_usage = (final_memory - initial_memory) / (1024 * 1024)  # MB

        # Verify memory usage is reasonable
        file_size = os.path.getsize(large_data_file) / (1024 * 1024)  # MB
        assert memory_usage < file_size * 2, f"Memory usage too high: {memory_usage:.1f}MB"


class TestResourceExhaustion:
    """Test resource exhaustion scenarios"""

    def test_memory_pressure(self, server: StringSearchServer) -> None:
        """Test behavior under memory pressure"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Create memory pressure
        data = []
        try:
            while True:
                data.append(b"x" * 1000000)  # Allocate 1MB chunks
                current_memory = process.memory_info().rss
                if current_memory - initial_memory > 1024 * 1024 * 1024:  # 1GB
                    break
        except MemoryError:
            pass

        # Verify server still functions
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

        # Clean up
        del data

    def test_file_descriptor_exhaustion(self, server: StringSearchServer) -> None:
        """Test behavior when file descriptors are exhausted"""
        # Open many file descriptors
        files = []
        try:
            while True:
                files.append(open(os.devnull))
        except OSError:
            pass

        try:
            # Verify server still accepts connections
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                assert sock.recv(1024)
        finally:
            # Clean up
            for f in files:
                f.close()

    def test_cpu_exhaustion(self, server: StringSearchServer) -> None:
        """Test behavior under CPU exhaustion"""
        def cpu_stress() -> None:
            while True:
                _ = sum(i * i for i in range(10000))

        # Start CPU stress threads
        stress_threads = []
        for _ in range(os.cpu_count() or 4):
            thread = threading.Thread(target=cpu_stress)
            thread.daemon = True
            thread.start()
            stress_threads.append(thread)

        # Verify server remains responsive
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)
        response_time = time.time() - start_time

        # Verify response time is reasonable
        assert response_time < 1.0, f"Response too slow under CPU load: {response_time:.2f}s"


class TestLongRunningOperations:
    """Test long-running operations"""

    def test_extended_session(self, server: StringSearchServer) -> None:
        """Test extended client session"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Run for 5 minutes
            end_time = time.time() + 300
            while time.time() < end_time:
                sock.send(b"test\n")
                assert sock.recv(1024)
                time.sleep(0.1)

    def test_continuous_reload(self, server: StringSearchServer, large_data_file: Path) -> None:
        """Test continuous data reloading"""
        server.config.file_path = large_data_file

        def client_worker() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                while True:
                    try:
                        sock.send(b"test\n")
                        assert sock.recv(1024)
                        time.sleep(0.1)
                    except Exception:
                        break

        # Start client threads
        clients = []
        for _ in range(10):
            thread = threading.Thread(target=client_worker)
            thread.daemon = True
            thread.start()
            clients.append(thread)

        # Continuously reload data
        for _ in range(10):
            server.load_data()
            time.sleep(1)

    def test_slow_client(self, server: StringSearchServer) -> None:
        """Test handling of slow clients"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            # Send query one byte at a time
            query = b"test\n"
            for byte in query:
                sock.send(bytes([byte]))
                time.sleep(0.1)
            
            assert sock.recv(1024)


class TestErrorConditions:
    """Test error conditions"""

    def test_invalid_queries(self, server: StringSearchServer) -> None:
        """Test handling of invalid queries"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            
            invalid_queries = [
                b"\x00\xff\n",  # Binary data
                b"" * 1000000 + b"\n",  # Very long query
                b"\n" * 1000,  # Many empty lines
                b"test",  # Missing newline
                b"test\ntest\n"  # Multiple lines
            ]
            
            for query in invalid_queries:
                sock.send(query)
                response = sock.recv(1024)
                assert b"error" in response.lower()

    def test_connection_errors(self, server: StringSearchServer) -> None:
        """Test handling of connection errors"""
        def error_session() -> None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 44445))
            
            # Send partial query and close
            sock.send(b"te")
            sock.close()

        # Run multiple error sessions
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=error_session)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Verify server still accepts connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_rapid_connect_disconnect(self, server: StringSearchServer) -> None:
        """Test rapid connect/disconnect cycles"""
        for _ in range(1000):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 44445))
            sock.close()

        # Verify server still works
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 