#!/usr/bin/env python3

"""
Load Tests

This module tests server performance under load:
1. Concurrent users
2. Sustained load
3. Burst load
4. Resource utilization
5. Recovery behavior
"""

import pytest
import socket
import threading
import time
import statistics
import psutil
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, List, Dict, Tuple
from dataclasses import dataclass

from server import StringSearchServer


@dataclass
class LoadTestResult:
    """Container for load test results"""
    requests_per_second: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    cpu_usage: float
    memory_usage: float


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


class TestConcurrentUsers:
    """Test server performance with concurrent users"""

    def test_increasing_users(self, server: StringSearchServer) -> None:
        """Test performance with increasing number of concurrent users"""
        def user_session(results_queue: queue.Queue) -> None:
            times = []
            errors = 0
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(100):
                    try:
                        start = time.perf_counter()
                        sock.send(b"test\n")
                        response = sock.recv(1024)
                        duration = time.perf_counter() - start
                        times.append(duration)
                        if not response:
                            errors += 1
                    except Exception:
                        errors += 1
            results_queue.put((times, errors))

        # Test with different numbers of concurrent users
        concurrent_users = [1, 10, 50, 100, 500]
        results: Dict[int, LoadTestResult] = {}
        
        process = psutil.Process()
        
        for users in concurrent_users:
            results_queue: queue.Queue = queue.Queue()
            start_time = time.time()
            
            # Start user threads
            with ThreadPoolExecutor(max_workers=users) as executor:
                futures = [
                    executor.submit(user_session, results_queue) 
                    for _ in range(users)
                ]
                for f in futures:
                    f.result()
            
            # Collect results
            all_times = []
            total_errors = 0
            while not results_queue.empty():
                times, errors = results_queue.get()
                all_times.extend(times)
                total_errors += errors
            
            # Calculate metrics
            duration = time.time() - start_time
            rps = (users * 100) / duration
            avg_time = statistics.mean(all_times)
            p95_time = statistics.quantiles(all_times, n=20)[18]  # 95th percentile
            p99_time = statistics.quantiles(all_times, n=100)[98]  # 99th percentile
            error_rate = total_errors / (users * 100)
            cpu_percent = process.cpu_percent()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            results[users] = LoadTestResult(
                requests_per_second=rps,
                average_response_time=avg_time,
                p95_response_time=p95_time,
                p99_response_time=p99_time,
                error_rate=error_rate,
                cpu_usage=cpu_percent,
                memory_usage=memory_usage
            )
            
            # Print results
            print(f"\nResults for {users} concurrent users:")
            print(f"Requests per second: {rps:.2f}")
            print(f"Average response time: {avg_time*1000:.2f}ms")
            print(f"95th percentile response time: {p95_time*1000:.2f}ms")
            print(f"99th percentile response time: {p99_time*1000:.2f}ms")
            print(f"Error rate: {error_rate*100:.2f}%")
            print(f"CPU usage: {cpu_percent:.1f}%")
            print(f"Memory usage: {memory_usage:.1f}MB")
            
            # Verify performance requirements
            assert avg_time < 0.1, f"Average response time too high: {avg_time*1000:.2f}ms"
            assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.2f}%"
            assert cpu_percent < 80, f"CPU usage too high: {cpu_percent:.1f}%"

    def test_connection_pool(self, server: StringSearchServer) -> None:
        """Test connection pool behavior under load"""
        def make_connection() -> Tuple[socket.socket, float]:
            start = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 44445))
            return sock, time.perf_counter() - start

        # Create many connections
        connection_times = []
        sockets = []
        try:
            for _ in range(1000):
                sock, duration = make_connection()
                sockets.append(sock)
                connection_times.append(duration)
        finally:
            for sock in sockets:
                sock.close()

        # Analyze connection times
        avg_time = statistics.mean(connection_times)
        p95_time = statistics.quantiles(connection_times, n=20)[18]
        
        # Verify performance
        assert avg_time < 0.01, f"Average connection time too high: {avg_time*1000:.2f}ms"
        assert p95_time < 0.05, f"95th percentile connection time too high: {p95_time*1000:.2f}ms"


class TestSustainedLoad:
    """Test server performance under sustained load"""

    def test_long_running_load(self, server: StringSearchServer) -> None:
        """Test performance during long-running load"""
        def generate_load(duration: int, results_queue: queue.Queue) -> None:
            times = []
            errors = 0
            end_time = time.time() + duration
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                while time.time() < end_time:
                    try:
                        start = time.perf_counter()
                        sock.send(b"test\n")
                        response = sock.recv(1024)
                        duration = time.perf_counter() - start
                        times.append(duration)
                        if not response:
                            errors += 1
                    except Exception:
                        errors += 1
            
            results_queue.put((times, errors))

        # Run load test for 5 minutes
        results_queue: queue.Queue = queue.Queue()
        duration = 300  # 5 minutes
        num_threads = 10
        
        process = psutil.Process()
        start_time = time.time()
        
        # Start load threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(
                target=generate_load,
                args=(duration, results_queue)
            )
            thread.start()
            threads.append(thread)

        # Monitor performance
        monitoring_data = []
        while any(t.is_alive() for t in threads):
            monitoring_data.append({
                'cpu_percent': process.cpu_percent(),
                'memory_usage': process.memory_info().rss,
                'time': time.time() - start_time
            })
            time.sleep(1)

        # Wait for threads to finish
        for thread in threads:
            thread.join()

        # Collect results
        all_times = []
        total_errors = 0
        while not results_queue.empty():
            times, errors = results_queue.get()
            all_times.extend(times)
            total_errors += errors

        # Calculate metrics
        total_requests = len(all_times)
        rps = total_requests / duration
        avg_time = statistics.mean(all_times)
        p95_time = statistics.quantiles(all_times, n=20)[18]
        error_rate = total_errors / total_requests
        avg_cpu = statistics.mean(d['cpu_percent'] for d in monitoring_data)
        avg_memory = statistics.mean(d['memory_usage'] for d in monitoring_data) / 1024 / 1024

        # Print results
        print("\nSustained Load Test Results:")
        print(f"Duration: {duration} seconds")
        print(f"Total requests: {total_requests}")
        print(f"Requests per second: {rps:.2f}")
        print(f"Average response time: {avg_time*1000:.2f}ms")
        print(f"95th percentile response time: {p95_time*1000:.2f}ms")
        print(f"Error rate: {error_rate*100:.2f}%")
        print(f"Average CPU usage: {avg_cpu:.1f}%")
        print(f"Average memory usage: {avg_memory:.1f}MB")

        # Verify performance
        assert avg_time < 0.1, f"Average response time too high: {avg_time*1000:.2f}ms"
        assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.2f}%"
        assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"


class TestBurstLoad:
    """Test server performance under burst load"""

    def test_request_bursts(self, server: StringSearchServer) -> None:
        """Test handling of request bursts"""
        def send_burst(size: int) -> Tuple[List[float], int]:
            times = []
            errors = 0
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                
                # Send burst of requests
                for _ in range(size):
                    try:
                        start = time.perf_counter()
                        sock.send(b"test\n")
                        response = sock.recv(1024)
                        duration = time.perf_counter() - start
                        times.append(duration)
                        if not response:
                            errors += 1
                    except Exception:
                        errors += 1
            
            return times, errors

        # Test different burst sizes
        burst_sizes = [100, 500, 1000, 5000]
        results: Dict[int, LoadTestResult] = {}
        
        process = psutil.Process()
        
        for size in burst_sizes:
            # Send burst
            times, errors = send_burst(size)
            
            # Calculate metrics
            rps = size / sum(times)
            avg_time = statistics.mean(times)
            p95_time = statistics.quantiles(times, n=20)[18]
            p99_time = statistics.quantiles(times, n=100)[98]
            error_rate = errors / size
            cpu_percent = process.cpu_percent()
            memory_usage = process.memory_info().rss / 1024 / 1024
            
            results[size] = LoadTestResult(
                requests_per_second=rps,
                average_response_time=avg_time,
                p95_response_time=p95_time,
                p99_response_time=p99_time,
                error_rate=error_rate,
                cpu_usage=cpu_percent,
                memory_usage=memory_usage
            )
            
            # Print results
            print(f"\nResults for burst size {size}:")
            print(f"Requests per second: {rps:.2f}")
            print(f"Average response time: {avg_time*1000:.2f}ms")
            print(f"95th percentile response time: {p95_time*1000:.2f}ms")
            print(f"99th percentile response time: {p99_time*1000:.2f}ms")
            print(f"Error rate: {error_rate*100:.2f}%")
            print(f"CPU usage: {cpu_percent:.1f}%")
            print(f"Memory usage: {memory_usage:.1f}MB")
            
            # Verify performance
            assert avg_time < 0.1, f"Average response time too high: {avg_time*1000:.2f}ms"
            assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.2f}%"
            assert cpu_percent < 80, f"CPU usage too high: {cpu_percent:.1f}%"


class TestResourceUtilization:
    """Test resource utilization under load"""

    def test_memory_usage(self, server: StringSearchServer) -> None:
        """Test memory usage patterns"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        def generate_load() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(1000):
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Generate load with multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_load)
            thread.start()
            threads.append(thread)

        # Monitor memory usage
        memory_samples = []
        while any(t.is_alive() for t in threads):
            memory_samples.append(process.memory_info().rss)
            time.sleep(0.1)

        # Wait for threads to finish
        for thread in threads:
            thread.join()

        # Calculate memory growth
        final_memory = process.memory_info().rss
        max_memory = max(memory_samples)
        memory_growth = (max_memory - initial_memory) / 1024 / 1024  # MB
        
        # Verify memory usage
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f}MB"

    def test_cpu_usage(self, server: StringSearchServer) -> None:
        """Test CPU usage patterns"""
        process = psutil.Process()
        
        def generate_load() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                for _ in range(1000):
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Generate load with multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_load)
            thread.start()
            threads.append(thread)

        # Monitor CPU usage
        cpu_samples = []
        while any(t.is_alive() for t in threads):
            cpu_samples.append(process.cpu_percent())
            time.sleep(0.1)

        # Wait for threads to finish
        for thread in threads:
            thread.join()

        # Calculate CPU usage statistics
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # Verify CPU usage
        assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"
        assert max_cpu < 95, f"Maximum CPU usage too high: {max_cpu:.1f}%"


class TestRecoveryBehavior:
    """Test recovery behavior after high load"""

    def test_recovery_time(self, server: StringSearchServer) -> None:
        """Test server recovery after high load"""
        def generate_load(duration: int) -> None:
            end_time = time.time() + duration
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                while time.time() < end_time:
                    sock.send(b"test\n")
                    sock.recv(1024)

        # Generate high load
        load_duration = 60  # 1 minute
        threads = []
        for _ in range(50):  # 50 concurrent clients
            thread = threading.Thread(
                target=generate_load,
                args=(load_duration,)
            )
            thread.start()
            threads.append(thread)

        # Wait for load to finish
        for thread in threads:
            thread.join()

        # Measure recovery
        recovery_times = []
        for _ in range(100):
            start = time.perf_counter()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.send(b"test\n")
                sock.recv(1024)
            recovery_times.append(time.perf_counter() - start)

        # Calculate recovery metrics
        avg_time = statistics.mean(recovery_times)
        p95_time = statistics.quantiles(recovery_times, n=20)[18]
        
        # Verify recovery
        assert avg_time < 0.01, f"Recovery time too high: {avg_time*1000:.2f}ms"
        assert p95_time < 0.05, f"95th percentile recovery time too high: {p95_time*1000:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 