"""Observability setup for OpenTelemetry, metrics, and structured logging."""

import logging
import time
from typing import Dict, Any, Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry
import structlog

from .config import settings

# Prometheus metrics
REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Business metrics
HOLDS_CREATED = Counter(
    'booking_holds_created_total',
    'Total booking holds created',
    ['departure_id'],
    registry=REGISTRY
)

HOLDS_EXPIRED = Counter(
    'booking_holds_expired_total',
    'Total booking holds expired',
    registry=REGISTRY
)

BOOKINGS_CONFIRMED = Counter(
    'bookings_confirmed_total',
    'Total bookings confirmed',
    ['departure_id'],
    registry=REGISTRY
)

BOOKINGS_CANCELLED = Counter(
    'bookings_cancelled_total',
    'Total bookings cancelled',
    registry=REGISTRY
)

ACTIVE_HOLDS = Gauge(
    'booking_holds_active',
    'Number of active holds',
    registry=REGISTRY
)

WAITLIST_ENTRIES = Gauge(
    'waitlist_entries_total',
    'Number of waitlist entries',
    ['departure_id'],
    registry=REGISTRY
)

CAPACITY_UTILIZATION = Gauge(
    'departure_capacity_utilization',
    'Capacity utilization percentage',
    ['departure_id'],
    registry=REGISTRY
)


def setup_structured_logging():
    """Configure structured logging with structlog."""
    
    def add_request_id(logger, method_name, event_dict):
        """Add request ID to log events."""
        # This will be set by middleware
        request_id = getattr(logger, '_request_id', None)
        if request_id:
            event_dict['request_id'] = request_id
        return event_dict
    
    def add_trace_context(logger, method_name, event_dict):
        """Add trace context to log events."""
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            event_dict['trace_id'] = format(ctx.trace_id, '032x')
            event_dict['span_id'] = format(ctx.span_id, '016x')
        return event_dict
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_request_id,
            add_trace_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_tracing(app_name: str = "tour-booking-api"):
    """Setup OpenTelemetry tracing."""
    
    # Create resource
    resource = Resource.create({
        "service.name": app_name,
        "service.version": "1.0.0",
        "environment": settings.environment,
    })
    
    # Setup tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    
    # Setup OTLP exporter (if OTLP endpoint is configured)
    if hasattr(settings, 'otlp_endpoint') and settings.otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Get tracer
    tracer = trace.get_tracer(__name__)
    return tracer


def setup_metrics(app_name: str = "tour-booking-api"):
    """Setup OpenTelemetry metrics."""
    
    # Create resource
    resource = Resource.create({
        "service.name": app_name,
        "service.version": "1.0.0",
        "environment": settings.environment,
    })
    
    # Setup OTLP metric exporter (if configured)
    if hasattr(settings, 'otlp_endpoint') and settings.otlp_endpoint:
        otlp_exporter = OTLPMetricExporter(endpoint=settings.otlp_endpoint)
        reader = PeriodicExportingMetricReader(exporter=otlp_exporter, export_interval_millis=60000)
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
    
    # Get meter
    meter = metrics.get_meter(__name__)
    return meter


def instrument_fastapi(app):
    """Instrument FastAPI with OpenTelemetry."""
    FastAPIInstrumentor.instrument_app(app)
    

def instrument_sqlalchemy():
    """Instrument SQLAlchemy with OpenTelemetry."""
    SQLAlchemyInstrumentor().instrument()


class MetricsCollector:
    """Collector for business metrics."""
    
    @staticmethod
    def record_hold_created(departure_id: str):
        """Record a hold creation."""
        HOLDS_CREATED.labels(departure_id=departure_id).inc()
    
    @staticmethod
    def record_hold_expired():
        """Record a hold expiration."""
        HOLDS_EXPIRED.inc()
    
    @staticmethod
    def record_booking_confirmed(departure_id: str):
        """Record a booking confirmation."""
        BOOKINGS_CONFIRMED.labels(departure_id=departure_id).inc()
    
    @staticmethod
    def record_booking_cancelled():
        """Record a booking cancellation."""
        BOOKINGS_CANCELLED.inc()
    
    @staticmethod
    def set_active_holds(count: int):
        """Set the number of active holds."""
        ACTIVE_HOLDS.set(count)
    
    @staticmethod
    def set_waitlist_entries(departure_id: str, count: int):
        """Set the number of waitlist entries for a departure."""
        WAITLIST_ENTRIES.labels(departure_id=departure_id).set(count)
    
    @staticmethod
    def set_capacity_utilization(departure_id: str, utilization: float):
        """Set capacity utilization percentage for a departure."""
        CAPACITY_UTILIZATION.labels(departure_id=departure_id).set(utilization)


def get_prometheus_metrics():
    """Get Prometheus metrics for the /metrics endpoint."""
    return generate_latest(REGISTRY)


# Global metrics collector instance
metrics_collector = MetricsCollector()


class StructuredLogger:
    """Structured logger with business context."""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(message, **kwargs)
    
    def with_context(self, **kwargs):
        """Add context to logger."""
        return StructuredLogger(self.logger.bind(**kwargs))


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)