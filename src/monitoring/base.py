"""Base monitoring classes"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .metrics import MetricValue


@dataclass
class HealthStatus:
    """Health check status"""
    healthy: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HealthCheck(ABC):
    """Base health check class"""
    
    @abstractmethod
    def check_health(self) -> HealthStatus:
        """Check health status"""
        pass


class PerformanceMonitor(ABC):
    """Base performance monitor class"""
    
    @abstractmethod
    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value"""
        pass
    
    @abstractmethod
    def get_metrics(self, window: Optional[float] = None) -> Dict[str, MetricValue]:
        """Get metrics within time window"""
        pass 