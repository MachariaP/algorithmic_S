#!/usr/bin/env python3

"""
Comprehensive Test Suite

This module contains extensive tests covering:
1. Edge cases and boundary conditions
2. Performance under various loads
3. Memory usage patterns
4. Concurrency behavior
5. Error handling scenarios
"""

import pytest
import socket
import ssl
import time
import threading
import resource
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, List, Tuple

from server import StringSearchServer
from src.config.config import Config


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


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_string(self, server: StringSearchServer) -> None:
        """Test empty string handling"""
        assert server._cached_search("") is False

    def test_very_long_string(self, server: StringSearchServer) -> None:
        """Test very long string handling"""
        long_string = "x" * 1023  # Just under buffer limit
        assert server._cached_search(long_string) is False

    def test_special_characters(self, server: StringSearchServer) -> None:
        """Test special character handling"""
        special_chars = ['\\', '"', "'", '\n', '\t', '\0', ';', '|', '&']
        for char in special_chars:
            assert server._cached_search(char) is False

    def test_unicode_strings(self, server: StringSearchServer) -> None:
        """Test Unicode string handling"""
        unicode_strings = ['你好', 'Привет', 'مرحبا', '🌟', 'αβγ']
        for string in unicode_strings:
            assert server._cached_search(string) is False


class TestPerformance:
    """Test performance characteristics"""

    def test_memory_usage(self, server: StringSearchServer) -> None:
        """Test memory usage patterns"""
        def get_memory_mb() -> float:
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

        initial_memory = get_memory_mb()
        
        # Perform intensive operations
        for _ in range(10000):
            server._cached_search("test_string")
        
        final_memory = get_memory_mb()
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100, f"Memory increase: {memory_increase}MB"

    def test_cache_effectiveness(self, server: StringSearchServer) -> None:
        """Test cache hit rates"""
        # Perform repeated searches
        test_string = "3;0;1;16;0;7;5;0"
        for _ in range(1000):
            server._cached_search(test_string)
        
        hit_rate = (server.cache_hits / server.total_searches) * 100
        assert hit_rate > 80, f"Cache hit rate too low: {hit_rate}%"

    @pytest.mark.parametrize("size", [10000, 50000, 100000])
    def test_scaling_performance(self, server: StringSearchServer, size: int) -> None:
        """Test performance scaling with data size"""
        data = [f"{i};0;1" for i in range(size)]
        start = time.perf_counter()
        
        for line in data[:100]:  # Test sample
            server._cached_search(line)
        
        duration = (time.perf_counter() - start) / 100
        assert duration < 0.5, f"Average search time: {duration*1000:.2f}ms"


class TestConcurrency:
    """Test concurrent behavior"""

    def test_parallel_searches(self, server: StringSearchServer) -> None:
        """Test parallel search performance"""
        def worker() -> List[float]:
            times = []
            for _ in range(100):
                start = time.perf_counter()
                server._cached_search("test_string")
                times.append(time.perf_counter() - start)
            return times

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: worker(), range(10)))

        # Analyze results
        all_times = [t for worker_times in results for t in worker_times]
        avg_time = sum(all_times) / len(all_times)
        assert avg_time < 0.001, f"Average parallel search time: {avg_time*1000:.2f}ms"

    def test_connection_limits(self, server: StringSearchServer) -> None:
        """Test connection limit handling"""
        connections = []
        try:
            # Try to exceed connection limit
            for _ in range(10100):  # Just over limit
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 44445))
                connections.append(sock)
        except (ConnectionRefusedError, OSError):
            pass
        finally:
            for sock in connections:
                sock.close()

        assert len(connections) <= 10000, "Connection limit exceeded"


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_queries(self, server: StringSearchServer) -> None:
        """Test handling of invalid queries"""
        invalid_queries = [
            None,
            b"\xff\xff",  # Invalid UTF-8
            object(),
            123,
            True
        ]
        
        for query in invalid_queries:
            with pytest.raises(Exception):
                server._cached_search(query)  # type: ignore

    def test_file_modifications(self, server: StringSearchServer, tmp_path: Path) -> None:
        """Test handling of file modifications"""
        # Create temporary data file
        data_file = tmp_path / "test.txt"
        data_file.write_text("test_line\n")
        
        # Modify server config
        server.config.file_path = data_file
        server.config.reread_on_query = True
        
        # Initial search
        assert server._cached_search("test_line") is True
        
        # Modify file
        data_file.write_text("new_line\n")
        
        # Search should reflect changes
        assert server._cached_search("test_line") is False
        assert server._cached_search("new_line") is True

    def test_resource_cleanup(self, server: StringSearchServer) -> None:
        """Test resource cleanup"""
        def count_open_files() -> int:
            return len(list(Path('/proc/self/fd').iterdir()))
        
        initial_files = count_open_files()
        
        # Perform operations
        for _ in range(100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 44445))
                sock.sendall(b"test\n")
                sock.recv(1024)
        
        final_files = count_open_files()
        assert final_files <= initial_files + 5, "File descriptors not properly cleaned up"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
