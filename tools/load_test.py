#!/usr/bin/env python3

"""
Load Testing Tool for String Search Server

Tests server performance under concurrent load with different patterns:
- Constant load
- Step load
- Spike load
- Random load
"""

import socket
import time
import random
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from rich.table import Table
from dataclasses import dataclass
from typing import List, Dict
import matplotlib.pyplot as plt
import logging
from pathlib import Path
import re
from collections import deque

# Test configuration
TEST_DURATION = 60  # seconds
RAMP_UP_TIME = 5   # seconds
MAX_WORKERS = 100
SAMPLE_RATE = 10   # measurements per second

# Test queries (mix of existing and non-existing)
TEST_QUERIES = [
    # Known existing strings
    "1;0;1;26;0;19;4;0;",
    "7;0;1;26;0;24;5;0;",
    "16;0;6;28;0;17;3;0;",
    "1;0;6;16;0;19;3;0;",
    # Variations that don't exist
    "1;0;6;16;0;19;3;0",  # Missing semicolon
    "nonexistent_1",
    "16;0;6;28;0;17;3;1;",  # Changed last number
]

console = Console()

@dataclass
class TestResult:
    timestamp: float
    response_time: float
    success: bool
    error: str = ""

class LoadTest:
    def __init__(self, host='localhost', port=44445):
        self.host = host
        self.port = port
        self.results: List[TestResult] = []
        self._lock = threading.Lock()
        self._connection_pool = deque(maxlen=MAX_WORKERS)
        
    def _get_connection(self) -> socket.socket:
        """Get connection from pool or create new one"""
        with self._lock:
            if self._connection_pool:
                return self._connection_pool.pop()
                
        sock = socket.create_connection((self.host, self.port), timeout=5.0)
        return sock
        
    def _return_connection(self, sock: socket.socket):
        """Return connection to pool"""
        with self._lock:
            try:
                sock.send(b'')  # Test if still alive
                self._connection_pool.append(sock)
            except:
                try:
                    sock.close()
                except:
                    pass
                    
    def make_request(self, query: str) -> TestResult:
        """Make a single request with connection pooling"""
        start_time = time.perf_counter()
        timestamp = start_time
        
        try:
            sock = self._get_connection()
            try:
                sock.sendall(query.encode() + b'\n')
                response = sock.recv(1024).decode().strip()
                exec_time = (time.perf_counter() - start_time) * 1000
                success = response == "STRING EXISTS"
                return TestResult(timestamp, exec_time, success)
            finally:
                self._return_connection(sock)
        except Exception as e:
            exec_time = (time.perf_counter() - start_time) * 1000
            return TestResult(timestamp, exec_time, False, str(e))
            
    def constant_load(self, requests_per_second: int):
        """Run constant load test"""
        console.print(f"\n[bold blue]Running constant load test at {requests_per_second} RPS")
        
        with Progress(SpinnerColumn(), *Progress.get_default_columns()) as progress:
            task = progress.add_task("Testing", total=TEST_DURATION)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                start_time = time.perf_counter()
                
                while time.perf_counter() - start_time < TEST_DURATION:
                    # Submit batch of requests
                    for _ in range(requests_per_second // SAMPLE_RATE):
                        query = random.choice(TEST_QUERIES)
                        future = executor.submit(self.make_request, query)
                        future.add_done_callback(self._record_result)
                    
                    # Wait for next interval
                    progress.update(task, advance=1)
                    time.sleep(1.0 / SAMPLE_RATE)
                    
    def step_load(self, start_rps: int, end_rps: int, steps: int):
        """Run step load test"""
        console.print(f"\n[bold blue]Running step load test from {start_rps} to {end_rps} RPS")
        
        step_duration = TEST_DURATION / steps
        rps_increment = (end_rps - start_rps) / steps
        
        for step in range(steps):
            rps = start_rps + (step * rps_increment)
            console.print(f"[cyan]Step {step + 1}: {rps:.0f} RPS")
            self.constant_load(int(rps))
            
    def spike_load(self, base_rps: int, spike_rps: int):
        """Run spike load test"""
        console.print(f"\n[bold blue]Running spike load test ({base_rps} → {spike_rps} RPS)")
        
        # Warm up
        self.constant_load(base_rps)
        
        # Spike
        self.constant_load(spike_rps)
        
        # Cool down
        self.constant_load(base_rps)
        
    def random_load(self, min_rps: int, max_rps: int, duration: int = TEST_DURATION):
        """Run random varying load test"""
        console.print(f"\n[bold blue]Running random load test ({min_rps}-{max_rps} RPS)")
        
        with Progress(SpinnerColumn(), *Progress.get_default_columns()) as progress:
            task = progress.add_task("Testing", total=duration)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                start_time = time.perf_counter()
                
                while time.perf_counter() - start_time < duration:
                    # Random RPS for this interval
                    rps = random.randint(min_rps, max_rps)
                    
                    # Submit batch of requests
                    for _ in range(rps // SAMPLE_RATE):
                        query = random.choice(TEST_QUERIES)
                        future = executor.submit(self.make_request, query)
                        future.add_done_callback(self._record_result)
                    
                    progress.update(task, advance=1)
                    time.sleep(1.0 / SAMPLE_RATE)
                    
    def analyze_results(self) -> Dict:
        """Enhanced results analysis"""
        if not self.results:
            return {}
            
        response_times = [r.response_time for r in self.results]
        successes = sum(1 for r in self.results if r.success)
        errors = [r.error for r in self.results if r.error]
        
        # Calculate requests per second over time
        timestamps = [r.timestamp for r in self.results]
        if timestamps:
            duration = max(timestamps) - min(timestamps)
            rps = len(self.results) / duration if duration > 0 else 0
        else:
            rps = 0
            
        return {
            "total_requests": len(self.results),
            "success_rate": (successes / len(self.results)) * 100,
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[-1],
            "p99_response_time": statistics.quantiles(response_times, n=100)[-1],
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "std_dev": statistics.stdev(response_times),
            "requests_per_second": rps,
            "error_count": len(errors),
            "unique_errors": len(set(errors))
        }
        
    def _record_result(self, future):
        """Record test result thread-safely"""
        with self._lock:
            self.results.append(future.result())
            
    def plot_results(self, output_path: str):
        """Generate performance plots"""
        # Response time over time
        plt.figure(figsize=(12, 6))
        times = [r.timestamp for r in self.results]
        response_times = [r.response_time for r in self.results]
        plt.plot(times, response_times, 'b.', alpha=0.1)
        plt.xlabel("Time (s)")
        plt.ylabel("Response Time (ms)")
        plt.title("Response Times Over Time")
        plt.grid(True)
        plt.savefig(f"{output_path}_response_times.png")
        plt.close()
        
        # Response time distribution
        plt.figure(figsize=(10, 6))
        plt.hist(response_times, bins=50)
        plt.xlabel("Response Time (ms)")
        plt.ylabel("Frequency")
        plt.title("Response Time Distribution")
        plt.grid(True)
        plt.savefig(f"{output_path}_distribution.png")
        plt.close()

def main():
    """Enhanced load testing"""
    test = LoadTest()
    
    # Run different load patterns
    patterns = [
        ("Constant Load", lambda: test.constant_load(100)),
        ("Step Load", lambda: test.step_load(50, 200, 5)),
        ("Spike Load", lambda: test.spike_load(50, 300)),
        ("Random Load", lambda: test.random_load(50, 150))
    ]
    
    for name, pattern in patterns:
        console.print(f"\n[bold cyan]Running {name}")
        pattern()
        results = test.analyze_results()
        
        # Print results table
        table = Table(title=f"{name} Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for metric, value in results.items():
            if isinstance(value, float):
                table.add_row(metric, f"{value:.2f}")
            else:
                table.add_row(metric, str(value))
                
        console.print(table)
        
        # Generate plots for this pattern
        test.plot_results(f"load_test_{name.lower().replace(' ', '_')}")
        
        # Clear results for next pattern
        test.results.clear()
    
    console.print("\n[green]Load testing complete! Check load_test_*.png for plots")

if __name__ == "__main__":
    main()
