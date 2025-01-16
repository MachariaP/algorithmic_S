#!/usr/bin/env python3

"""
Performance Limit Tests

This module tests performance limits and degradation:
1. Maximum throughput
2. Response time degradation
3. Memory growth patterns
4. Resource utilization
5. System limits
"""

import pytest
import socket
import time
import threading
import psutil
import resource
import statistics
from pathlib import Path
from typing import Generator, List, Dict
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


class TestThroughputLimits:
    """Test maximum throughput capabilities"""

    def test_max_rps(self, server: StringSearchServer) -> None:
        """Test maximum requests per second"""
        def make_requests(n: int) -> List[float]:
            times = []
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(n):
                    start = time.perf_counter()
                    sock.send(b"test\n")
                    sock.recv(1024)
                    times.append(time.perf_counter() - start)
            return times

        # Test with increasing concurrent clients
        concurrent_clients = [1, 10, 50, 100, 500, 1000]
        results: Dict[int, List[float]] = {}
        
        for clients in concurrent_clients:
            with ThreadPoolExecutor(max_workers=clients) as executor:
                futures = [executor.submit(make_requests, 100) for _ in range(clients)]
                client_times = [t for f in futures for t in f.result()]
                results[clients] = client_times

            # Calculate statistics
            avg_time = statistics.mean(results[clients])
            p95_time = statistics.quantiles(results[clients], n=20)[18]  # 95th percentile
            rps = clients * 100 / sum(results[clients])
            
            print(f"\nClients: {clients}")
            print(f"Average response time: {avg_time*1000:.2f}ms")
            print(f"95th percentile: {p95_time*1000:.2f}ms")
            print(f"Requests per second: {rps:.2f}")

            # Verify performance requirements
            assert avg_time < 0.1, f"Average response time too high: {avg_time*1000:.2f}ms"
            assert p95_time < 0.2, f"95th percentile too high: {p95_time*1000:.2f}ms"
            assert rps > 1000, f"RPS too low: {rps:.2f}"

    def test_sustained_load(self, server: StringSearchServer) -> None:
        """Test performance under sustained load"""
        def generate_load(duration: int) -> List[float]:
            times = []
            end_time = time.time() + duration
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                while time.time() < end_time:
                    start = time.perf_counter()
                    sock.send(b"test\n")
                    sock.recv(1024)
                    times.append(time.perf_counter() - start)
            return times

        # Run sustained load for 5 minutes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_load, 300) for _ in range(10)]
            all_times = [t for f in futures for t in f.result()]

        # Analyze performance stability
        time_windows = [all_times[i:i+1000] for i in range(0, len(all_times), 1000)]
        averages = [statistics.mean(window) for window in time_windows]
        
        # Verify performance doesn't degrade
        assert max(averages) < 2 * min(averages), "Performance degraded significantly"


class TestResponseTimeDegradation:
    """Test response time degradation patterns"""

    def test_cache_impact(self, server: StringSearchServer) -> None:
        """Test impact of cache size on response times"""
        # Fill cache
        for i in range(server.config.cache_size * 2):
            query = f"test_string_{i}"
            start = time.perf_counter()
            server._cached_search(query)
            duration = time.perf_counter() - start
            
            if i < server.config.cache_size:
                assert duration < 0.001, "Uncached lookup too slow"
            else:
                # Verify cache eviction doesn't impact performance
                assert duration < 0.002, "Cache eviction impacting performance"

    def test_file_size_impact(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test impact of file size on response times"""
        file_sizes = [10000, 50000, 100000, 250000]
        times: Dict[int, List[float]] = {}

        for size in file_sizes:
            # Create test file
            test_file = tmp_path / f"test_{size}.txt"
            with open(test_file, 'w') as f:
                for i in range(size):
                    f.write(f"test_line_{i}\n")

            # Load file and measure search times
            server.config.file_path = test_file
            server.load_data()

            times[size] = []
            for _ in range(1000):
                start = time.perf_counter()
                server._cached_search("test_line_0")
                times[size].append(time.perf_counter() - start)

            avg_time = statistics.mean(times[size])
            assert avg_time < 0.001, f"Search too slow for {size} lines: {avg_time*1000:.2f}ms"


class TestMemoryGrowth:
    """Test memory growth patterns"""

    def test_memory_growth_rate(self, server: StringSearchServer) -> None:
        """Test memory growth under load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Generate load
        for i in range(10000):
            server._cached_search(f"test_string_{i}")
            
            if i % 1000 == 0:
                current_memory = process.memory_info().rss
                growth_rate = (current_memory - initial_memory) / (i + 1)
                assert growth_rate < 1000, f"Memory growth rate too high: {growth_rate:.2f} bytes/request"

    def test_memory_cleanup(self, server: StringSearchServer) -> None:
        """Test memory cleanup after load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Generate heavy load
        for i in range(100000):
            server._cached_search(f"test_string_{i}")

        # Force garbage collection
        import gc
        gc.collect()

        # Verify memory returns to reasonable level
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100 * 1024 * 1024, f"Memory not cleaned up: {memory_increase / 1024 / 1024:.2f}MB retained"


class TestResourceUtilization:
    """Test resource utilization patterns"""

    def test_cpu_utilization(self, server: StringSearchServer) -> None:
        """Test CPU utilization under load"""
        process = psutil.Process()
        
        def monitor_cpu():
            cpu_percentages = []
            end_time = time.time() + 60
            while time.time() < end_time:
                cpu_percentages.append(process.cpu_percent())
                time.sleep(0.1)
            return statistics.mean(cpu_percentages)

        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()

        # Generate load
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(lambda: [server._cached_search("test") for _ in range(1000)]) 
                for _ in range(10)
            ]
            for f in futures:
                f.result()

        monitor_thread.join()
        avg_cpu = monitor_thread.result()  # type: ignore
        assert avg_cpu < 80, f"CPU utilization too high: {avg_cpu:.1f}%"

    def test_file_descriptor_usage(self, server: StringSearchServer) -> None:
        """Test file descriptor usage patterns"""
        def count_open_files() -> int:
            return len(list(Path('/proc/self/fd').iterdir()))

        initial_fds = count_open_files()
        
        # Create many connections
        sockets = []
        for _ in range(100):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 44445))
            sockets.append(sock)

        current_fds = count_open_files()
        fd_per_conn = (current_fds - initial_fds) / len(sockets)
        assert fd_per_conn <= 2, f"Too many file descriptors per connection: {fd_per_conn:.1f}"

        # Cleanup
        for sock in sockets:
            sock.close()


class TestSystemLimits:
    """Test system limit handling"""

    def test_max_connections(self, server: StringSearchServer) -> None:
        """Test maximum connection handling"""
        # Get system limits
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        
        # Try to exceed soft limit
        sockets = []
        try:
            for _ in range(soft_limit):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                sockets.append(sock)
        except (socket.error, OSError):
            pass
        finally:
            for sock in sockets:
                sock.close()

        # Verify server still functions
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            sock.send(b"test\n")
            assert sock.recv(1024)

    def test_max_memory(self, server: StringSearchServer) -> None:
        """Test maximum memory handling"""
        # Set memory limit
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
        new_limit = min(hard_limit, 1024 * 1024 * 1024)  # 1GB or hard limit
        resource.setrlimit(resource.RLIMIT_AS, (new_limit, hard_limit))

        # Try to exceed memory limit
        try:
            data = ["x" * 1000000 for _ in range(2000)]  # Try to allocate ~2GB
            for item in data:
                server._cached_search(item)
        except MemoryError:
            pass

        # Verify server still functions
        assert server._cached_search("test") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 