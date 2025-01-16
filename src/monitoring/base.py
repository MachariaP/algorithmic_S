"""Base monitoring classes"""

import time
import logging
import logging.handlers
import threading
import json
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path


@dataclass
class MetricValue:
    """Container for metric values"""
    value: float
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class PerformanceMonitor:
    """Base performance monitor"""
    
    def __init__(self):
        self._metrics: Dict[str, deque] = {
            "requests_per_second": deque(maxlen=1000),
            "average_response_time": deque(maxlen=1000),
            "error_rate": deque(maxlen=1000),
            "cache_hit_rate": deque(maxlen=1000),
            "memory_usage": deque(maxlen=1000),
            "cpu_usage": deque(maxlen=1000)
        }
        self._lock = threading.Lock()
        
    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=1000)
            self._metrics[name].append(MetricValue(value))
            
    def get_metrics(self) -> Dict[str, float]:
        """Get current metrics"""
        with self._lock:
            return {
                name: float(sum(m.value for m in values) / len(values)) if values else 0.0
                for name, values in self._metrics.items()
            }
            
    def export_metrics(self, file_path: str) -> None:
        """Export metrics to file"""
        metrics = self.get_metrics()
        with open(file_path, 'w') as f:
            json.dump(metrics, f, indent=2)


class HealthCheck:
    """Base health checker"""
    
    def __init__(self):
        self.memory_threshold = 90.0  # percent
        self.cpu_threshold = 80.0  # percent
        self.error_rate_threshold = 0.01  # 1%
        
    def check_health(self) -> Dict[str, Any]:
        """Check overall health"""
        status = "healthy"
        details = []
        
        # Check system resources
        process = psutil.Process()
        memory_usage = process.memory_percent()
        cpu_usage = process.cpu_percent()
        
        if memory_usage > self.memory_threshold:
            status = "unhealthy"
            details.append("high memory usage")
            
        if cpu_usage > self.cpu_threshold:
            status = "unhealthy"
            details.append("high cpu usage")
            
        return {
            "status": status,
            "memory_usage": memory_usage,
            "cpu_usage": cpu_usage,
            "details": details
        }


@dataclass
class Alert:
    """Alert notification"""
    message: str
    severity: str
    timestamp: float = 0.0
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
            
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlertManager:
    """Base alert manager"""
    
    def __init__(self, notifier: Optional[Any] = None):
        self._alerts: deque = deque(maxlen=1000)
        self._active_alerts: Dict[str, Alert] = {}
        self._lock = threading.Lock()
        self.notifier = notifier
        self.logger = logging.getLogger(__name__)
        
    def alert(self, message: str, severity: str = "warning") -> None:
        """Create and record an alert"""
        alert = Alert(message, severity)
        self._add_alert(alert)
        
    def _add_alert(self, alert: Alert) -> None:
        """Add new alert"""
        with self._lock:
            self._alerts.append(alert)
            self._active_alerts[alert.message] = alert
            
            if self.notifier:
                try:
                    self.notifier.send_notification(alert)
                except Exception as e:
                    self.logger.error(f"Failed to send alert notification: {e}")
                    
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history"""
        with self._lock:
            return [alert.to_dict() for alert in self._alerts]
            
    def check_alerts(self) -> List[str]:
        """Check for new alerts"""
        alerts = []
        process = psutil.Process()
        
        # Check CPU usage
        cpu_usage = process.cpu_percent()
        if cpu_usage > 90:
            alert = Alert(
                f"Critical: CPU usage at {cpu_usage}%",
                "critical"
            )
            self._add_alert(alert)
            alerts.append(alert.message)
            
        # Check memory usage
        memory_usage = process.memory_percent()
        if memory_usage > 90:
            alert = Alert(
                f"Critical: Memory usage at {memory_usage}%",
                "critical"
            )
            self._add_alert(alert)
            alerts.append(alert.message)
            
        return alerts 