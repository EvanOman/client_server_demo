"""Background worker for expiring holds."""

import logging
from datetime import datetime

from ..core.database import async_session_factory
from ..services.booking_service import BookingService
from .base import BaseWorker

logger = logging.getLogger(__name__)


class HoldExpiryWorker(BaseWorker):
    """
    Background worker that expires holds past their TTL.

    Runs periodically to find and expire active holds that have passed
    their expiration time, restoring capacity to departures.
    """

    def __init__(self, interval_seconds: int = 60):
        """
        Initialize the hold expiry worker.

        Args:
            interval_seconds: How often to check for expired holds (default: 60s)
        """
        super().__init__(name="HoldExpiry", interval_seconds=interval_seconds)

    async def process(self) -> None:
        """Process expired holds."""
        async with async_session_factory() as db:
            try:
                # Get current timestamp
                now = datetime.utcnow()

                # Create booking service with db session
                booking_service = BookingService(db)

                # Expire holds
                expired_count = await booking_service.expire_holds(db, now)

                if expired_count > 0:
                    logger.info(
                        f"Expired {expired_count} holds",
                        extra={
                            "expired_count": expired_count,
                            "timestamp": now.isoformat(),
                            "worker": self.name,
                        }
                    )

                await db.commit()

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Error expiring holds: {e!s}",
                    exc_info=True,
                    extra={"worker": self.name}
                )
                raise
