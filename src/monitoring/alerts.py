"""Alert system"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data"""
    level: AlertLevel
    source: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


class AlertNotifier(Protocol):
    """Protocol for alert notifiers"""
    def send_alert(self, alert: Alert) -> None:
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
        
    def send_alert(
        self,
        level_or_alert: Union[AlertLevel, Alert],
        source: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send alert to all notifiers
        
        Can be called with either:
        - An Alert object: send_alert(alert)
        - Individual parameters: send_alert(level, source, message, details=None)
        """
        if isinstance(level_or_alert, Alert):
            alert = level_or_alert
        else:
            if source is None or message is None:
                raise ValueError("source and message are required when not passing an Alert object")
            alert = Alert(level_or_alert, source, message, details)
            
        self.alerts.append(alert)
        
        # Trim alerts history
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
            
        # Send to notifiers
        for notifier in self.notifiers:
            try:
                notifier.send_alert(alert)
            except Exception as e:
                print(f"Error sending alert to notifier: {e}")
                
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