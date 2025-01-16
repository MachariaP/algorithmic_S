#!/usr/bin/env python3

"""Performance monitoring"""

import time
import psutil
import threading
from typing import Dict, List
from dataclasses import dataclass
from collections import deque


@dataclass
class Metrics:
    """Server metrics"""
    response_times: deque  # Rolling window of response times
    active_connections: int
    requests_per_second: float
    memory_usage: float
    cpu_usage: float


class ServerMonitor:
    """Monitor server performance"""

    def __init__(self, window_size: int = 1000):
        """Initialize monitor

        Args:
            window_size: Number of samples to keep
        """
        self.metrics = Metrics(
            response_times=deque(maxlen=window_size),
            active_connections=0,
            requests_per_second=0.0,
            memory_usage=0.0,
            cpu_usage=0.0
        )
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._request_count = 0

    def record_request(self, duration: float) -> None:
        """Record request duration"""
        with self._lock:
            self.metrics.response_times.append(duration)
            self._request_count += 1
            elapsed = time.time() - self._start_time
            self.metrics.requests_per_second = self._request_count / elapsed

    def update_system_metrics(self) -> None:
        """Update system resource usage"""
        process = psutil.Process()
        self.metrics.memory_usage =
        process.memory_info().rss / 1024 / 1024  # MB

        self.metrics.cpu_usage = process.cpu_percent()

    def get_metrics(self) -> Dict[str, float]:
        """Get current metrics"""
        with self._lock:
            times = list(self.metrics.response_times)
            return {
                "avg_response_time": sum(times) / len(times) if times else 0,
                "requests_per_second": self.metrics.requests_per_second,
                "memory_usage_mb": self.metrics.memory_usage,
                "cpu_usage_percent": self.metrics.cpu_usage
            }
