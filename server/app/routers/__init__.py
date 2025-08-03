"""FastAPI routers package."""

from .booking import router as booking_router
from .departure import router as departure_router
from .health import router as health_router
from .inventory import router as inventory_router
from .tour import router as tour_router
from .waitlist import router as waitlist_router

__all__ = [
    "booking_router",
    "departure_router",
    "health_router",
    "inventory_router",
    "tour_router",
    "waitlist_router",
]
