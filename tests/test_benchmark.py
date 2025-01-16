#!/usr/bin/env python3

"""
Benchmark Tests

This module provides benchmarking tests:
1. Search performance
2. Memory usage
3. Network throughput
4. Cache efficiency
5. Comparative analysis
"""

import pytest
import socket
import threading
import time
import tempfile
import os
import json
import statistics
import psutil
from pathlib import Path
from typing import Generator, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from src.server import StringSearchServer
from src.search import SearchEngine


@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    requests_per_second: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    memory_usage: float
    cpu_usage: float


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
def benchmark_data() -> Generator[Path, None, None]:
    """Fixture to create benchmark data file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        # Create dataset with known characteristics
        for i in range(250000):  # 250K lines
            if i % 4 == 0:
                temp_file.write(f"common_pattern_{i}\n")
            elif i % 4 == 1:
                temp_file.write(f"rare_pattern_{i}\n")
            elif i % 4 == 2:
                temp_file.write(f"unique_pattern_{i}\n")
            else:
                temp_file.write(f"random_text_{i}\n")
        temp_file.flush()
        yield Path(temp_file.name)
        os.unlink(temp_file.name)


class TestSearchPerformance:
    """Test search performance characteristics"""

    def test_search_latency(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test search latency under different conditions"""
        server.config.file_path = benchmark_data
        server.load_data()

        def measure_latency(query: str, iterations: int = 1000) -> Dict[str, float]:
            times = []
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(iterations):
                    start = time.perf_counter()
                    sock.send(f"{query}\n".encode())
                    sock.recv(1024)
                    times.append(time.perf_counter() - start)
            
            return {
                'avg': statistics.mean(times),
                'p95': statistics.quantiles(times, n=20)[18],
                'p99': statistics.quantiles(times, n=100)[98]
            }

        # Test different query patterns
        patterns = {
            'common': 'common_pattern_100',
            'rare': 'rare_pattern_101',
            'unique': 'unique_pattern_102',
            'nonexistent': 'nonexistent_pattern',
            'prefix': '^common',
            'suffix': 'pattern_100$',
            'regex': 'pattern_[0-9]+$'
        }

        results = {}
        for name, pattern in patterns.items():
            results[name] = measure_latency(pattern)
            
            # Verify performance requirements
            assert results[name]['avg'] < 0.001, f"Average latency too high for {name}"
            assert results[name]['p95'] < 0.002, f"P95 latency too high for {name}"
            assert results[name]['p99'] < 0.005, f"P99 latency too high for {name}"

    def test_throughput(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test maximum throughput"""
        server.config.file_path = benchmark_data
        server.load_data()

        def client_worker(duration: int) -> Dict[str, Any]:
            results = {'requests': 0, 'errors': 0, 'times': []}
            end_time = time.time() + duration
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                while time.time() < end_time:
                    try:
                        start = time.perf_counter()
                        sock.send(b"common_pattern_100\n")
                        response = sock.recv(1024)
                        results['times'].append(time.perf_counter() - start)
                        results['requests'] += 1
                        if not response:
                            results['errors'] += 1
                    except Exception:
                        results['errors'] += 1
            
            return results

        # Run concurrent clients
        duration = 60  # 1 minute
        num_clients = 50
        with ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(client_worker, duration) for _ in range(num_clients)]
            results = [future.result() for future in futures]

        # Aggregate results
        total_requests = sum(r['requests'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        all_times = [t for r in results for t in r['times']]

        # Calculate metrics
        rps = total_requests / duration
        error_rate = total_errors / total_requests if total_requests > 0 else 1.0
        avg_time = statistics.mean(all_times)
        p95_time = statistics.quantiles(all_times, n=20)[18]
        p99_time = statistics.quantiles(all_times, n=100)[98]

        # Verify performance requirements
        assert rps > 10000, f"Throughput too low: {rps:.2f} RPS"
        assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.2f}%"
        assert avg_time < 0.001, f"Average latency too high: {avg_time*1000:.2f}ms"
        assert p95_time < 0.002, f"P95 latency too high: {p95_time*1000:.2f}ms"
        assert p99_time < 0.005, f"P99 latency too high: {p99_time*1000:.2f}ms"


class TestMemoryUsage:
    """Test memory usage characteristics"""

    def test_memory_efficiency(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test memory efficiency"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Load data
        server.config.file_path = benchmark_data
        server.load_data()

        # Measure memory usage
        final_memory = process.memory_info().rss
        memory_per_line = (final_memory - initial_memory) / 250000  # bytes per line

        # Verify memory efficiency
        assert memory_per_line < 200, f"Memory usage per line too high: {memory_per_line:.1f} bytes"

    def test_memory_stability(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test memory stability under load"""
        server.config.file_path = benchmark_data
        server.load_data()

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        def generate_load() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(10000):
                    sock.send(b"common_pattern_100\n")
                    sock.recv(1024)

        # Run concurrent load
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_load)
            thread.start()
            threads.append(thread)

        # Monitor memory
        memory_samples = []
        while any(t.is_alive() for t in threads):
            memory_samples.append(process.memory_info().rss)
            time.sleep(0.1)

        for thread in threads:
            thread.join()

        # Calculate memory stability metrics
        max_memory = max(memory_samples)
        memory_growth = max_memory - initial_memory
        memory_volatility = statistics.stdev(memory_samples) / statistics.mean(memory_samples)

        # Verify memory stability
        assert memory_growth < 100 * 1024 * 1024, f"Excessive memory growth: {memory_growth/1024/1024:.1f}MB"
        assert memory_volatility < 0.1, f"High memory volatility: {memory_volatility:.2f}"


class TestNetworkThroughput:
    """Test network throughput characteristics"""

    def test_connection_throughput(self, server: StringSearchServer) -> None:
        """Test connection handling throughput"""
        def connection_cycle() -> float:
            start = time.perf_counter()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                sock.recv(1024)
            return time.perf_counter() - start

        # Measure connection throughput
        num_connections = 1000
        with ThreadPoolExecutor(max_workers=100) as executor:
            times = list(executor.map(lambda _: connection_cycle(), range(num_connections)))

        # Calculate metrics
        connections_per_second = num_connections / sum(times)
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        # Verify throughput requirements
        assert connections_per_second > 1000, f"Connection throughput too low: {connections_per_second:.2f} conn/s"
        assert avg_time < 0.01, f"Average connection time too high: {avg_time*1000:.2f}ms"
        assert p95_time < 0.02, f"P95 connection time too high: {p95_time*1000:.2f}ms"

    def test_data_throughput(self, server: StringSearchServer) -> None:
        """Test data transfer throughput"""
        def transfer_data(size: int) -> float:
            data = b"x" * size + b"\n"
            start = time.perf_counter()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(data)
                sock.recv(1024)
            return time.perf_counter() - start

        # Test different payload sizes
        sizes = [100, 1000, 10000, 100000]
        results = {}
        
        for size in sizes:
            times = []
            for _ in range(100):
                times.append(transfer_data(size))
            
            throughput = size / statistics.mean(times)  # bytes per second
            results[size] = throughput
            
            # Verify throughput scales reasonably
            assert throughput > size * 100, f"Throughput too low for {size} bytes: {throughput/1024/1024:.1f}MB/s"


class TestCacheEfficiency:
    """Test cache efficiency characteristics"""

    def test_cache_hit_ratio(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test cache hit ratio"""
        server.config.file_path = benchmark_data
        server.load_data()

        def measure_cache_performance(query: str, iterations: int) -> Dict[str, float]:
            times = []
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for i in range(iterations):
                    start = time.perf_counter()
                    sock.send(f"{query}\n".encode())
                    sock.recv(1024)
                    times.append(time.perf_counter() - start)
            
            # First query is cache miss, rest should be hits
            return {
                'miss_time': times[0],
                'hit_time_avg': statistics.mean(times[1:]),
                'hit_ratio': (iterations - 1) / iterations
            }

        # Test cache performance
        results = measure_cache_performance("common_pattern_100", 1000)
        
        # Verify cache efficiency
        assert results['hit_time_avg'] < results['miss_time'] * 0.1, "Cache hits not significantly faster"
        assert results['hit_ratio'] > 0.99, "Cache hit ratio too low"

    def test_cache_eviction(self, server: StringSearchServer, benchmark_data: Path) -> None:
        """Test cache eviction behavior"""
        server.config.file_path = benchmark_data
        server.load_data()
        
        # Fill cache with unique queries
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            for i in range(server.config.cache_size * 2):
                sock.send(f"unique_query_{i}\n".encode())
                sock.recv(1024)

        # Verify most recent queries are cached
        times = []
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', 44445))
            for i in range(server.config.cache_size):
                start = time.perf_counter()
                sock.send(f"unique_query_{server.config.cache_size + i}\n".encode())
                sock.recv(1024)
                times.append(time.perf_counter() - start)

        # Verify recent queries are fast (cached)
        avg_time = statistics.mean(times)
        assert avg_time < 0.001, f"Cache eviction not working efficiently: {avg_time*1000:.2f}ms"


class TestComparativeAnalysis:
    """Test comparative performance analysis"""

    def test_algorithm_comparison(self, benchmark_data: Path) -> None:
        """Compare different search algorithms"""
        # Load test data
        with open(benchmark_data, 'r') as f:
            data = f.readlines()

        def benchmark_algorithm(name: str, search_fn: Any) -> Dict[str, float]:
            times = []
            for _ in range(1000):
                start = time.perf_counter()
                search_fn("common_pattern_100")
                times.append(time.perf_counter() - start)
            
            return {
                'name': name,
                'avg_time': statistics.mean(times),
                'p95_time': statistics.quantiles(times, n=20)[18],
                'throughput': 1 / statistics.mean(times)
            }

        # Test different algorithms
        results = []
        
        # Hash table lookup (current implementation)
        engine = SearchEngine()
        engine.load_data(benchmark_data)
        results.append(benchmark_algorithm('hash_table', engine.search))
        
        # Simple list search
        def list_search(pattern: str) -> bool:
            return any(pattern in line for line in data)
        results.append(benchmark_algorithm('list_search', list_search))
        
        # Binary search (on sorted data)
        sorted_data = sorted(data)
        def binary_search(pattern: str) -> bool:
            import bisect
            i = bisect.bisect_left(sorted_data, pattern)
            return i < len(sorted_data) and sorted_data[i].startswith(pattern)
        results.append(benchmark_algorithm('binary_search', binary_search))

        # Compare results
        fastest = min(results, key=lambda x: x['avg_time'])
        assert fastest['name'] == 'hash_table', "Current implementation not fastest"
        
        # Export comparison results
        with open('algorithm_comparison.json', 'w') as f:
            json.dump(results, f, indent=2)


"""Benchmark tests"""

import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import pytest

from src.config.models import ServerConfig
from src.server import StringSearchServer


@pytest.fixture
def large_data_file(tmp_path: Path) -> Path:
    """Create large test data file"""
    data_file = tmp_path / "large_data.txt"
    with open(data_file, "w") as f:
        for i in range(1_000_000):
            f.write(f"test line {i}\n")
    return data_file


@pytest.fixture
def benchmark_server(
    server_config: ServerConfig,
    large_data_file: Path
) -> StringSearchServer:
    """Create server for benchmarking"""
    config = server_config.copy()
    config.data_file = large_data_file
    
    server = StringSearchServer(config)
    server.start()
    return server


def create_client(server: StringSearchServer) -> socket.socket:
    """Create client socket"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if server.config.security.ssl_enabled:
        ssl_wrapper = SSLWrapper(server.config.security)
        client = ssl_wrapper.wrap_socket(client, server_side=False)
    
    client.connect((server.config.host, server.config.port))
    return client


def send_search_request(client: socket.socket, pattern: str) -> dict:
    """Send search request and return response"""
    request = {
        "pattern": pattern,
        "options": {
            "case_sensitive": False,
            "whole_line": False,
            "regex": False
        }
    }
    data = json.dumps(request).encode() + b"\n"
    
    start_time = time.time()
    client.sendall(data)
    response = json.loads(client.recv(4096).decode())
    end_time = time.time()
    
    response["latency"] = end_time - start_time
    return response


@pytest.mark.benchmark
def test_search_latency(benchmark_server: StringSearchServer):
    """Test search latency"""
    client = create_client(benchmark_server)
    
    try:
        # Perform searches
        latencies = []
        for _ in range(100):
            response = send_search_request(client, "test")
            latencies.append(response["latency"])
        
        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Assert performance requirements
        assert avg_latency < 0.01  # 10ms average
        assert max_latency < 0.05  # 50ms maximum
        assert p95_latency < 0.02  # 20ms 95th percentile
        
    finally:
        client.close()


@pytest.mark.benchmark
def test_search_throughput(benchmark_server: StringSearchServer):
    """Test search throughput"""
    num_clients = 10
    requests_per_client = 100
    
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        # Create clients
        clients = [
            create_client(benchmark_server)
            for _ in range(num_clients)
        ]
        
        try:
            # Start timing
            start_time = time.time()
            
            # Submit search requests
            futures = []
            for client in clients:
                for _ in range(requests_per_client):
                    futures.append(
                        executor.submit(send_search_request, client, "test")
                    )
            
            # Wait for all requests to complete
            responses = [f.result() for f in futures]
            end_time = time.time()
            
            # Calculate throughput
            total_requests = num_clients * requests_per_client
            duration = end_time - start_time
            throughput = total_requests / duration
            
            # Assert performance requirements
            assert throughput > 1000  # At least 1000 requests per second
            
        finally:
            for client in clients:
                client.close()


@pytest.mark.benchmark
def test_concurrent_connections(benchmark_server: StringSearchServer):
    """Test concurrent connections"""
    num_clients = benchmark_server.config.resources.max_connections
    
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        # Create clients
        clients = []
        futures = []
        
        try:
            # Connect clients concurrently
            for _ in range(num_clients):
                futures.append(
                    executor.submit(create_client, benchmark_server)
                )
            
            # Wait for connections
            for future in futures:
                try:
                    client = future.result()
                    clients.append(client)
                except (ConnectionRefusedError, OSError):
                    break
            
            # Assert connection capacity
            assert len(clients) == num_clients
            
            # Test all connections work
            response_futures = []
            for client in clients:
                response_futures.append(
                    executor.submit(send_search_request, client, "test")
                )
            
            responses = [f.result() for f in response_futures]
            assert all("results" in r for r in responses)
            
        finally:
            for client in clients:
                client.close()


@pytest.mark.benchmark
def test_memory_usage(benchmark_server: StringSearchServer):
    """Test memory usage"""
    import psutil
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Perform searches to exercise memory
    client = create_client(benchmark_server)
    try:
        for _ in range(1000):
            send_search_request(client, "test")
        
        # Check memory usage
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # Assert memory requirements
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
        
    finally:
        client.close()


@pytest.mark.benchmark
def test_cpu_usage(benchmark_server: StringSearchServer):
    """Test CPU usage"""
    import psutil
    
    process = psutil.Process()
    
    # Perform searches to exercise CPU
    client = create_client(benchmark_server)
    try:
        start_time = time.time()
        start_cpu_time = sum(process.cpu_times()[:2])  # User + System time
        
        for _ in range(1000):
            send_search_request(client, "test")
        
        end_time = time.time()
        end_cpu_time = sum(process.cpu_times()[:2])
        
        # Calculate CPU usage
        elapsed_time = end_time - start_time
        cpu_time = end_cpu_time - start_cpu_time
        cpu_percent = (cpu_time / elapsed_time) * 100
        
        # Assert CPU requirements
        assert cpu_percent < 80  # Less than 80% CPU usage
        
    finally:
        client.close()


@pytest.mark.benchmark
def test_regex_performance(benchmark_server: StringSearchServer):
    """Test regex search performance"""
    client = create_client(benchmark_server)
    
    try:
        # Test different regex patterns
        patterns = [
            r"test.*\d+",      # Simple pattern
            r"test.*test.*\d+", # Multiple matches
            r"(test.*?){3}\d+", # Complex pattern
            r"\b\w+\d+\b",     # Word boundary
            r"[a-z]+\d+[a-z]+" # Character classes
        ]
        
        for pattern in patterns:
            request = {
                "pattern": pattern,
                "options": {
                    "case_sensitive": False,
                    "whole_line": False,
                    "regex": True
                }
            }
            data = json.dumps(request).encode() + b"\n"
            
            start_time = time.time()
            client.sendall(data)
            response = json.loads(client.recv(4096).decode())
            end_time = time.time()
            
            # Assert performance requirements
            assert end_time - start_time < 0.1  # Less than 100ms per regex search
            assert "results" in response
            
    finally:
        client.close()


@pytest.mark.benchmark
def test_large_response(benchmark_server: StringSearchServer):
    """Test handling of large response"""
    client = create_client(benchmark_server)
    
    try:
        # Search for common pattern to get many results
        response = send_search_request(client, "line")
        
        # Assert response handling
        assert len(response["results"]) > 1000
        assert response["latency"] < 0.1  # Less than 100ms for large response
        
    finally:
        client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 