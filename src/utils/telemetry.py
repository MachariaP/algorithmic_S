"""OpenTelemetry instrumentation setup"""

import socket
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.socket import SocketInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Custom attributes for the service
SERVICE_NAME = "string-search-server"
SERVICE_VERSION = "0.1.0"
DEPLOYMENT_ENVIRONMENT = "development"  # Should be configurable


def setup_telemetry(
    otlp_endpoint: Optional[str] = None,
    sample_ratio: float = 1.0,
    service_name: str = SERVICE_NAME,
    service_version: str = SERVICE_VERSION,
    deployment_environment: str = DEPLOYMENT_ENVIRONMENT,
) -> None:
    """Setup OpenTelemetry instrumentation
    
    Args:
        otlp_endpoint: OpenTelemetry collector endpoint
        sample_ratio: Sampling ratio (0.0 to 1.0)
        service_name: Service name
        service_version: Service version
        deployment_environment: Deployment environment
    """
    # Create resource
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": deployment_environment,
            "host.name": socket.gethostname(),
        }
    )

    # Create tracer provider with sampling
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBasedTraceIdRatio(sample_ratio),
    )

    # Add OTLP exporter if endpoint is provided
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Setup propagator
    propagator = TraceContextTextMapPropagator()
    trace.set_tracer_provider(provider)

    # Instrument libraries
    LoggingInstrumentor().instrument()
    SocketInstrumentor().instrument()


def get_tracer(name: str = SERVICE_NAME) -> trace.Tracer:
    """Get a tracer instance
    
    Args:
        name: Name for the tracer
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


class TracingContextManager:
    """Context manager for tracing operations"""

    def __init__(
        self,
        span_name: str,
        tracer: Optional[trace.Tracer] = None,
        attributes: Optional[dict] = None,
    ):
        self.span_name = span_name
        self.tracer = tracer or get_tracer()
        self.attributes = attributes or {}
        self.span: Optional[trace.Span] = None

    def __enter__(self) -> trace.Span:
        """Start a new span"""
        self.span = self.tracer.start_span(self.span_name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End the span"""
        if self.span:
            if exc_val:
                self.span.set_status(
                    Status(StatusCode.ERROR, str(exc_val))
                )
                self.span.record_exception(exc_val)
            self.span.end()


def trace_method(name: Optional[str] = None, attributes: Optional[dict] = None):
    """Decorator for tracing methods
    
    Args:
        name: Name for the span (defaults to method name)
        attributes: Additional attributes to add to the span
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with TracingContextManager(span_name, attributes=attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class SearchSpanAttributes:
    """Constants for search span attributes"""
    PATTERN = "search.pattern"
    CASE_SENSITIVE = "search.case_sensitive"
    WHOLE_LINE = "search.whole_line"
    USE_REGEX = "search.use_regex"
    RESULT_COUNT = "search.result_count"
    DURATION = "search.duration"
    CACHE_HIT = "search.cache_hit"


class ServerSpanAttributes:
    """Constants for server span attributes"""
    CLIENT_IP = "server.client_ip"
    REQUEST_ID = "server.request_id"
    METHOD = "server.method"
    PATH = "server.path"
    STATUS_CODE = "server.status_code"
    ERROR_TYPE = "server.error_type"
    ERROR_MESSAGE = "server.error_message" 