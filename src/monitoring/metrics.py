"""Metrics collection and management"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import deque


@dataclass
class MetricValue:
    """Container for metric values"""
    value: float
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class MetricsManager:
    """Manage metrics collection and storage"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self._metrics: Dict[str, deque] = {}
        
    def start(self) -> None:
        """Start metrics collection"""
        pass  # Placeholder for Prometheus setup
        
    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value"""
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=1000)
        self._metrics[name].append(MetricValue(value))
        
    def get_metrics(self, window: Optional[float] = None) -> Dict[str, List[MetricValue]]:
        """Get metrics within time window"""
        result = {}
        now = time.time()
        
        for name, values in self._metrics.items():
            if window is None:
                result[name] = list(values)
            else:
                result[name] = [
                    v for v in values
                    if now - v.timestamp <= window
                ]
                
        return result
