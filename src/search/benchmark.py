"""Benchmark functionality for search engine performance testing"""

import time
import statistics
import psutil
from dataclasses import dataclass
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

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

class SearchBenchmark:
    """Benchmark utilities for search operations"""
    
    def __init__(self, search_engine):
        self.search_engine = search_engine
        self.process = psutil.Process()
        
    def measure_latency(self, query: str, iterations: int = 1000) -> Dict[str, float]:
        """Measure search latency for a query"""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            self.search_engine.search(query)
            times.append(time.perf_counter() - start)
            
        return {
            'avg': statistics.mean(times),
            'p95': statistics.quantiles(times, n=20)[18],
            'p99': statistics.quantiles(times, n=100)[98]
        }
        
    def measure_throughput(self, duration: int, num_clients: int = 50) -> BenchmarkResult:
        """Measure search throughput under concurrent load"""
        def client_worker(duration: int) -> Dict[str, Any]:
            results = {'requests': 0, 'errors': 0, 'times': []}
            end_time = time.time() + duration
            
            while time.time() < end_time:
                try:
                    start = time.perf_counter()
                    self.search_engine.search("test")
                    results['times'].append(time.perf_counter() - start)
                    results['requests'] += 1
                except Exception:
                    results['errors'] += 1
                    
            return results
            
        with ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(client_worker, duration) for _ in range(num_clients)]
            results = [future.result() for future in futures]
            
        total_requests = sum(r['requests'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        all_times = [t for r in results for t in r['times']]
        
        return BenchmarkResult(
            requests_per_second=total_requests / duration,
            average_response_time=statistics.mean(all_times),
            p95_response_time=statistics.quantiles(all_times, n=20)[18],
            p99_response_time=statistics.quantiles(all_times, n=100)[98],
            error_rate=total_errors / total_requests if total_requests > 0 else 1.0,
            memory_usage=self.process.memory_info().rss,
            cpu_usage=self.process.cpu_percent()
        )
        
    def measure_memory_efficiency(self, data_size: int) -> float:
        """Measure memory usage per line of data"""
        initial_memory = self.process.memory_info().rss
        
        # Generate test data
        test_data = [f"test_line_{i}" for i in range(data_size)]
        self.search_engine.data = set(test_data)
        
        final_memory = self.process.memory_info().rss
        return (final_memory - initial_memory) / data_size
        
    def measure_memory_stability(self, duration: int, num_threads: int = 10) -> Dict[str, float]:
        """Measure memory stability under load"""
        initial_memory = self.process.memory_info().rss
        memory_samples = []
        
        def generate_load():
            end_time = time.time() + duration
            while time.time() < end_time:
                self.search_engine.search("test")
                
        threads = []
        for _ in range(num_threads):
            thread = ThreadPoolExecutor(max_workers=1).submit(generate_load)
            threads.append(thread)
            
        while any(not t.done() for t in threads):
            memory_samples.append(self.process.memory_info().rss)
            time.sleep(0.1)
            
        return {
            'max_growth': max(memory_samples) - initial_memory,
            'volatility': statistics.stdev(memory_samples) / statistics.mean(memory_samples)
        } 