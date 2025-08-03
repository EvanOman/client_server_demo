"""Metrics endpoint for Prometheus scraping."""

from fastapi import APIRouter, Response

from ..core.observability import get_prometheus_metrics

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Endpoint for Prometheus to scrape metrics",
    response_class=Response,
    tags=["Observability"]
)
async def metrics():
    """
    Return Prometheus metrics.
    
    Returns:
        Response: Prometheus metrics in text format
    """
    metrics_data = get_prometheus_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )