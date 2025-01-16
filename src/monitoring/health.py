"""Health check system"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check data"""
    name: str
    status: HealthStatus
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()


class HealthChecker(Protocol):
    """Protocol for health checkers"""
    def check_health(self) -> HealthCheck:
        """Perform health check"""
        ...


class HealthManager:
    """Health check manager"""
    
    def __init__(self):
        """Initialize health manager"""
        self.checkers: List[HealthChecker] = []
        self.checks: List[HealthCheck] = []
        
    def add_checker(self, checker: HealthChecker) -> None:
        """Add health checker"""
        self.checkers.append(checker)
        
    def check_health(self) -> Dict[str, Any]:
        """Run all health checks"""
        self.checks = []
        
        for checker in self.checkers:
            check = checker.check_health()
            self.checks.append(check)
            
        return self._build_health_report()
        
    def _build_health_report(self) -> Dict[str, Any]:
        """Build health check report"""
        # Determine overall status
        if any(c.status == HealthStatus.CRITICAL for c in self.checks):
            status = HealthStatus.CRITICAL
        elif any(c.status == HealthStatus.WARNING for c in self.checks):
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
            
        # Build report
        return {
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "details": check.details or {},
                    "timestamp": check.timestamp.isoformat()
                }
                for check in self.checks
            ]
        }
        
    def get_checks(
        self,
        status: Optional[HealthStatus] = None,
        name: Optional[str] = None
    ) -> List[HealthCheck]:
        """Get filtered health checks"""
        checks = self.checks
        
        if status:
            checks = [c for c in checks if c.status == status]
            
        if name:
            checks = [c for c in checks if c.name == name]
            
        return checks 