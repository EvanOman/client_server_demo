"""Background worker for processing waitlist entries."""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session_factory
from ..models.departure import Departure
from ..services.waitlist_service import WaitlistService
from .base import BaseWorker

logger = logging.getLogger(__name__)


class WaitlistWorker(BaseWorker):
    """
    Background worker that processes waitlist entries when capacity becomes available.
    
    Monitors departures with waitlists and automatically creates holds for
    waitlisted customers when seats become available.
    """
    
    def __init__(self, interval_seconds: int = 30):
        """
        Initialize the waitlist worker.
        
        Args:
            interval_seconds: How often to check waitlists (default: 30s)
        """
        super().__init__(name="Waitlist", interval_seconds=interval_seconds)
    
    async def process(self) -> None:
        """Process waitlist entries for departures with available capacity."""
        async with async_session_factory() as db:
            try:
                # Find departures with both available capacity and waitlist entries
                departures = await self._find_departures_with_waitlist_and_capacity(db)
                
                if not departures:
                    return
                
                logger.info(
                    f"Processing waitlists for {len(departures)} departures",
                    extra={
                        "departure_count": len(departures),
                        "worker": self.name,
                    }
                )
                
                total_processed = 0
                
                # Create waitlist service with db session
                waitlist_service = WaitlistService(db)
                
                # Process each departure
                for departure in departures:
                    try:
                        result = await waitlist_service.process_waitlist(
                            db, 
                            departure.id
                        )
                        
                        if result.processed_count > 0:
                            logger.info(
                                f"Processed {result.processed_count} waitlist entries for departure {departure.id}",
                                extra={
                                    "departure_id": departure.id,
                                    "processed_count": result.processed_count,
                                    "holds_created": len(result.holds_created),
                                    "worker": self.name,
                                }
                            )
                            total_processed += result.processed_count
                            
                    except Exception as e:
                        logger.error(
                            f"Error processing waitlist for departure {departure.id}: {str(e)}",
                            exc_info=True,
                            extra={
                                "departure_id": departure.id,
                                "worker": self.name,
                            }
                        )
                
                if total_processed > 0:
                    await db.commit()
                    logger.info(
                        f"Total waitlist entries processed: {total_processed}",
                        extra={
                            "total_processed": total_processed,
                            "worker": self.name,
                        }
                    )
                    
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Error in waitlist worker: {str(e)}",
                    exc_info=True,
                    extra={"worker": self.name}
                )
                raise
    
    async def _find_departures_with_waitlist_and_capacity(
        self, 
        db: AsyncSession
    ) -> List[Departure]:
        """
        Find departures that have both available capacity and waitlist entries.
        
        Args:
            db: Database session
            
        Returns:
            List of departures to process
        """
        # Query for departures with available capacity that have waitlist entries
        query = (
            select(Departure)
            .where(Departure.capacity_available > 0)
            .join(Departure.waitlist_entries)
            .distinct()
            .limit(100)  # Process up to 100 departures per iteration
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())