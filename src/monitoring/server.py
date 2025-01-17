"""Server monitoring implementation"""

import time
import psutil
from typing import Dict, Any, Optional, List
from collections import deque

from .base import HealthCheck, HealthStatus, PerformanceMonitor
from .metrics import MetricValue
from .alerts import Alert, AlertLevel, AlertManager


class ServerPerformanceMonitor(PerformanceMonitor):
    """Server performance monitor"""
    
    def __init__(self, server):
        self.server = server
        self._metrics: Dict[str, deque] = {}
        
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


class ServerHealthCheck(HealthCheck):
    """Server health checker"""
    
    def __init__(self, server):
        self.server = server
        self.error_rate_threshold = 0.1  # 10%
        self.memory_threshold = 80.0  # 80%
        self.cpu_threshold = 80.0  # 80%
        
    def check_system_health(self) -> Dict[str, Any]:
        """Check system health metrics"""
        process = psutil.Process()
        
        memory_percent = process.memory_percent()
        cpu_percent = process.cpu_percent()
        
        healthy = True
        details = []
        
        if memory_percent > self.memory_threshold:
            healthy = False
            details.append(f"high memory usage: {memory_percent:.1f}%")
            
        if cpu_percent > self.cpu_threshold:
            healthy = False
            details.append(f"high CPU usage: {cpu_percent:.1f}%")
            
        return HealthStatus(
            healthy=healthy,
            message="System health check",
            details={
                "memory_percent": memory_percent,
                "cpu_percent": cpu_percent,
                "issues": details
            }
        )
        
    def check_health(self) -> HealthStatus:
        """Check overall health"""
        system_health = self.check_system_health()
        
        return HealthStatus(
            healthy=system_health.healthy,
            message="Server health check",
            details={
                "system": system_health.details
            }
        )


class ServerAlertManager:
    """Server alert manager"""
    
    def __init__(self, server):
        self.server = server
        self.alert_manager = AlertManager()
        self.performance_monitor = ServerPerformanceMonitor(server)
        self.health_check = ServerHealthCheck(server)
        
    def send_alert(self, alert: Alert) -> None:
        """Send an alert"""
        self.alert_manager.send_alert(alert)
        
    def check_alerts(self) -> None:
        """Check for alert conditions"""
        # Check system health
        health = self.health_check.check_health()
        if not health.healthy:
            self.alert_manager.send_alert(
                Alert(
                    level=AlertLevel.WARNING,
                    source="system",
                    message="System health check failed",
                    details=health.details
                )
            )
            
        # Check error rate
        metrics = self.performance_monitor.get_metrics(window=60)  # Last minute
        if "error_rate" in metrics:
            error_values = [m.value for m in metrics["error_rate"]]
            if error_values:
                avg_error_rate = sum(error_values) / len(error_values)
                if avg_error_rate > self.health_check.error_rate_threshold:
                    self.alert_manager.send_alert(
                        Alert(
                            level=AlertLevel.WARNING,
                            source="server",
                            message="High error rate detected",
                            details={"error_rate": avg_error_rate}
                        )
                    ) 