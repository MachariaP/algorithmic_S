"""Server monitoring and metrics"""

import time
import logging
import threading
import json
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


class MetricsCollector:
    """Collect and track metrics"""
    def __init__(self, max_history: int = 1000):
        self._metrics: Dict[str, deque] = {}
        self._max_history = max_history
        self._lock = threading.Lock()

    def record(self, name: str, value: float) -> None:
        """Record a metric value"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque(maxlen=self._max_history)
            self._metrics[name].append(MetricValue(value))

    def get(self, name: str, window: Optional[float] = None) -> List[MetricValue]:
        """Get metric values within time window"""
        with self._lock:
            if name not in self._metrics:
                return []
            if window is None:
                return list(self._metrics[name])
            now = time.time()
            return [m for m in self._metrics[name] if now - m.timestamp <= window]


@dataclass
class HealthStatus:
    """Health check status"""
    healthy: bool
    message: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class HealthChecker:
    """Health check manager"""
    def __init__(self):
        self._checks = {}
        self._thresholds = {}
        self._lock = threading.Lock()

    def add_check(self, name: str, check_fn: callable, threshold: Optional[float] = None) -> None:
        """Add a health check"""
        with self._lock:
            self._checks[name] = check_fn
            if threshold is not None:
                self._thresholds[name] = threshold

    def check(self, name: Optional[str] = None) -> Dict[str, HealthStatus]:
        """Run health checks"""
        with self._lock:
            if name:
                if name not in self._checks:
                    raise KeyError(f"No such health check: {name}")
                return {name: self._run_check(name)}
            return {name: self._run_check(name) for name in self._checks}

    def _run_check(self, name: str) -> HealthStatus:
        """Run a single health check"""
        try:
            result = self._checks[name]()
            if name in self._thresholds:
                threshold = self._thresholds[name]
                healthy = result <= threshold
                message = f"Value {result} {'within' if healthy else 'exceeds'} threshold {threshold}"
                return HealthStatus(healthy, message, {'value': result, 'threshold': threshold})
            return HealthStatus(True, "Check passed", {'value': result})
        except Exception as e:
            return HealthStatus(False, str(e))


@dataclass
class Alert:
    """Alert notification"""
    name: str
    message: str
    level: str
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class AlertManager:
    """Alert management system"""
    def __init__(self, max_history: int = 1000):
        self._alerts = deque(maxlen=max_history)
        self._handlers = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def add_handler(self, handler: callable) -> None:
        """Add alert handler"""
        with self._lock:
            self._handlers.append(handler)

    def alert(self, name: str, message: str, level: str = "warning") -> None:
        """Trigger an alert"""
        alert = Alert(name, message, level)
        with self._lock:
            self._alerts.append(alert)
            for handler in self._handlers:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert handler: {e}")

    def get_history(self, count: Optional[int] = None) -> List[Alert]:
        """Get alert history"""
        with self._lock:
            alerts = list(self._alerts)
            if count:
                alerts = alerts[-count:]
            return alerts


class MonitoringManager:
    """Central monitoring manager"""
    def __init__(self, log_dir: Optional[Path] = None):
        self.metrics = MetricsCollector()
        self.health = HealthChecker()
        self.alerts = AlertManager()
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_file = self.log_dir / "server.log"
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
    def generate_report(self, report_type: str = "all") -> Dict[str, Any]:
        """Generate monitoring report"""
        report = {
            'timestamp': time.time(),
            'type': report_type
        }
        
        if report_type in ('all', 'metrics'):
            report['metrics'] = {
                name: [asdict(m) for m in self.metrics.get(name)]
                for name in ('latency', 'throughput', 'memory_usage', 'cpu_usage')
            }
            
        if report_type in ('all', 'health'):
            report['health'] = {
                name: asdict(status)
                for name, status in self.health.check().items()
            }
            
        if report_type in ('all', 'alerts'):
            report['alerts'] = [
                asdict(alert) for alert in self.alerts.get_history()
            ]
            
        return report
        
    def save_report(self, report_type: str = "all") -> Path:
        """Generate and save monitoring report"""
        report = self.generate_report(report_type)
        report_file = self.log_dir / f"{report_type}_report_{int(time.time())}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        return report_file 