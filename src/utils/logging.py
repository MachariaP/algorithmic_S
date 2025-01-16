#!/usr/bin/env python3

"""Structured logging configuration with request tracking"""

import logging
import logging.handlers
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import structlog
from structlog.types import Processor

from ..config.models import LogConfig


def setup_logging(config: LogConfig) -> None:
    """Configure structured logging"""
    # Create log directory if it doesn't exist
    config.directory.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, config.level),
        format=config.format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                config.directory / "server.log",
                maxBytes=config.max_size,
                backupCount=config.backup_count,
            ),
        ],
    )

    # Configure structlog pre-processors
    pre_chain: list[Processor] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name to event dict
        structlog.stdlib.add_logger_name,
        # Add timestamp to event dict
        structlog.processors.TimeStamper(fmt="iso"),
        # Add caller info to event dict
        structlog.processors.CallsiteParameterAdder(
            parameters={"filename", "module", "function", "lineno"}
        ),
    ]

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level_number,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class RequestContext:
    """Request context for tracking request-specific information"""

    def __init__(self) -> None:
        self.request_id: Optional[str] = None
        self.start_time: Optional[float] = None
        self.client_ip: Optional[str] = None
        self.method: Optional[str] = None
        self.path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "method": self.method,
            "path": self.path,
            "duration": time.time() - self.start_time if self.start_time else None,
        }


class RequestContextFilter(logging.Filter):
    """Logging filter that adds request context to log records"""

    def __init__(self) -> None:
        super().__init__()
        self.context = RequestContext()

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record"""
        context_dict = self.context.to_dict()
        for key, value in context_dict.items():
            setattr(record, key, value)
        return True


@contextmanager
def request_context(
    method: str = "", path: str = "", client_ip: str = ""
) -> Generator[RequestContext, None, None]:
    """Context manager for tracking request context"""
    context = RequestContext()
    context.request_id = str(uuid.uuid4())
    context.start_time = time.time()
    context.method = method
    context.path = path
    context.client_ip = client_ip

    # Get the request context filter
    logger = logging.getLogger()
    context_filter = None
    for filter in logger.filters:
        if isinstance(filter, RequestContextFilter):
            context_filter = filter
            break

    if context_filter is None:
        context_filter = RequestContextFilter()
        logger.addFilter(context_filter)

    # Set the current context
    previous_context = context_filter.context
    context_filter.context = context

    try:
        yield context
    finally:
        # Restore the previous context
        context_filter.context = previous_context


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance"""
    return structlog.get_logger(name)
