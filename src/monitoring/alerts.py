"""Alert system"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data"""
    level: AlertLevel
    source: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()


class AlertNotifier(Protocol):
    """Protocol for alert notifiers"""
    def send_notification(self, alert: Alert) -> None:
        """Send alert notification"""
        ...


class AlertManager:
    """Alert manager"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.notifiers: List[AlertNotifier] = []
        self.alerts: List[Alert] = []
        
    def add_notifier(self, notifier: AlertNotifier) -> None:
        """Add alert notifier"""
        self.notifiers.append(notifier)
        
    def send_alert(self, alert: Alert) -> None:
        """Send alert to all notifiers"""
        self.alerts.append(alert)
        
        for notifier in self.notifiers:
            notifier.send_notification(alert)
            
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        source: Optional[str] = None
    ) -> List[Alert]:
        """Get filtered alerts"""
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
            
        if source:
            alerts = [a for a in alerts if a.source == source]
            
        return alerts 