"""Health check system"""

import os
import psutil
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class HealthMetrics:
    """System health metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    open_files: int
    thread_count: int
    timestamp: datetime

class HealthCheck:
    """Health check manager"""
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self._thresholds = thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 80.0, 
            'disk_usage_percent': 80.0,
            'open_files': 1000,
            'thread_count': 100
        }
        self._process = psutil.Process(os.getpid())
        self._history: List[HealthMetrics] = []
        
    def check(self) -> HealthMetrics:
        """Collect current health metrics"""
        metrics = HealthMetrics(
            cpu_percent=self._process.cpu_percent(),
            memory_percent=self._process.memory_percent(),
            disk_usage_percent=psutil.disk_usage('/').percent,
            open_files=len(self._process.open_files()),
            thread_count=self._process.num_threads(),
            timestamp=datetime.now()
        )
        self._history.append(metrics)
        if len(self._history) > 1000:
            self._history.pop(0)
        return metrics
        
    def is_healthy(self) -> bool:
        """Check if current metrics are within thresholds"""
        metrics = self.check()
        return all([
            metrics.cpu_percent < self._thresholds['cpu_percent'],
            metrics.memory_percent < self._thresholds['memory_percent'],
            metrics.disk_usage_percent < self._thresholds['disk_usage_percent'],
            metrics.open_files < self._thresholds['open_files'],
            metrics.thread_count < self._thresholds['thread_count']
        ])
        
    def get_history(self) -> List[HealthMetrics]:
        """Get historical health metrics"""
        return self._history.copy()
        
    def set_threshold(self, metric: str, value: float) -> None:
        """Update threshold for a metric"""
        if metric not in self._thresholds:
            raise ValueError(f"Invalid metric: {metric}")
        self._thresholds[metric] = value 