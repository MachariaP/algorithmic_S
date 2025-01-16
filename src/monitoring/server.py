"""Server-specific monitoring"""

import time
import psutil
from typing import Dict, Any, List, Optional

from .base import PerformanceMonitor, HealthCheck, AlertManager, Alert


class ServerPerformanceMonitor(PerformanceMonitor):
    """Server-specific performance monitor"""
    
    def __init__(self, server):
        super().__init__()
        self.server = server
        
    def get_metrics(self) -> Dict[str, float]:
        """Get server metrics"""
        metrics = super().get_metrics()
        
        # Add server-specific metrics
        total_time = time.time() - self.server.start_time
        total_requests = self.server.request_count
        
        if total_time > 0:
            metrics["requests_per_second"] = total_requests / total_time
            
        if total_requests > 0:
            metrics["error_rate"] = self.server.error_count / total_requests
            metrics["cache_hit_rate"] = self.server.cache_hits / total_requests
            metrics["average_response_time"] = self.server.total_response_time / total_requests
            
        return metrics


class ServerHealthCheck(HealthCheck):
    """Server-specific health checker"""
    
    def __init__(self, server):
        super().__init__()
        self.server = server
        
    def check_server_health(self) -> Dict[str, Any]:
        """Check server component health"""
        return {
            "status": "healthy" if self.server._running.is_set() else "unhealthy",
            "details": {
                "running": self.server._running.is_set(),
                "port": self.server.config.port,
                "max_connections": self.server.config.max_connections
            }
        }
        
    def check_cache_health(self) -> Dict[str, Any]:
        """Check cache component health"""
        return {
            "status": "healthy",
            "details": {
                "size": self.server.search_engine.cache_size,
                "hit_rate": (
                    self.server.cache_hits / self.server.request_count
                    if self.server.request_count > 0 else 0
                )
            }
        }
        
    def check_search_health(self) -> Dict[str, Any]:
        """Check search engine component health"""
        return {
            "status": "healthy" if self.server.search_engine.is_loaded() else "unhealthy",
            "details": {
                "data_loaded": self.server.search_engine.is_loaded(),
                "index_size": self.server.search_engine.index_size
            }
        }
        
    def check_health(self) -> Dict[str, Any]:
        """Check overall server health"""
        health = super().check_health()
        
        # Check server components
        server_health = self.check_server_health()
        cache_health = self.check_cache_health()
        search_health = self.check_search_health()
        
        if not all(h["status"] == "healthy" for h in [server_health, cache_health, search_health]):
            health["status"] = "unhealthy"
            
        # Check error rate
        if self.server.request_count > 0:
            error_rate = self.server.error_count / self.server.request_count
            if error_rate > self.error_rate_threshold:
                health["status"] = "unhealthy"
                health["details"].append("high error rate")
                
        # Add component status
        health["components"] = {
            "server": server_health,
            "cache": cache_health,
            "search": search_health
        }
        
        return health


class ServerAlertManager(AlertManager):
    """Server-specific alert manager"""
    
    def __init__(self, server, notifier: Optional[Any] = None):
        super().__init__(notifier)
        self.server = server
        
    def check_alerts(self) -> List[str]:
        """Check for server-specific alerts"""
        alerts = super().check_alerts()
        
        # Check error rate
        if self.server.request_count > 0:
            error_rate = self.server.error_count / self.server.request_count
            if error_rate > 0.1:  # 10% error rate
                alert = Alert(
                    f"Warning: High error rate at {error_rate*100}%",
                    "warning"
                )
                self._add_alert(alert)
                alerts.append(alert.message)
                
        # Check connection count
        if len(self.server.clients) >= self.server.config.max_connections * 0.9:
            alert = Alert(
                "Warning: Connection pool near capacity",
                "warning"
            )
            self._add_alert(alert)
            alerts.append(alert.message)
            
        return alerts 