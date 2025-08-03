"""Base worker class for background tasks."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Abstract base class for background workers.
    
    Provides common functionality for running periodic background tasks.
    """
    
    def __init__(self, name: str, interval_seconds: int = 60):
        """
        Initialize the worker.
        
        Args:
            name: Worker name for logging
            interval_seconds: How often to run the task
        """
        self.name = name
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    @abstractmethod
    async def process(self) -> None:
        """Process one iteration of the background task."""
        pass
    
    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            logger.warning(f"{self.name} worker is already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"{self.name} worker started with {self.interval_seconds}s interval")
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            logger.warning(f"{self.name} worker is not running")
            return
            
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logger.info(f"{self.name} worker stopped")
    
    async def _run(self) -> None:
        """Main worker loop."""
        logger.info(f"{self.name} worker loop started")
        
        while self._running:
            try:
                start_time = datetime.utcnow()
                await self.process()
                
                # Calculate processing time
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"{self.name} worker iteration completed",
                    extra={
                        "duration_seconds": duration,
                        "worker": self.name,
                    }
                )
                
                # Sleep for the remaining interval time
                sleep_time = max(0, self.interval_seconds - duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
            except asyncio.CancelledError:
                logger.info(f"{self.name} worker loop cancelled")
                break
            except Exception as e:
                logger.error(
                    f"{self.name} worker error: {str(e)}",
                    exc_info=True,
                    extra={"worker": self.name}
                )
                # Wait before retrying on error
                await asyncio.sleep(self.interval_seconds)