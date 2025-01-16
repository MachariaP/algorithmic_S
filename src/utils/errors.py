"""Error classes"""

from typing import Any, Dict, Optional


class ServerError(Exception):
    """Base class for server errors"""
    def __init__(
        self,
        message: str,
        code: str = "SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConfigError(ServerError):
    """Configuration error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details=details
        )


class SecurityError(ServerError):
    """Security-related error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="SECURITY_ERROR",
            details=details
        )


class ValidationError(ServerError):
    """Validation error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )


class RateLimitError(ServerError):
    """Rate limit exceeded error"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class ResourceError(ServerError):
    """Resource-related error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RESOURCE_ERROR",
            details=details
        )


class ConnectionError(ServerError):
    """Connection-related error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="CONNECTION_ERROR",
            details=details
        )


class SearchError(ServerError):
    """Search-related error"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="SEARCH_ERROR",
            details=details
        ) 