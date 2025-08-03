"""Worker manager for coordinating background tasks."""

import asyncio
import logging
from typing import Dict, List

from .base import BaseWorker
from .hold_expiry_worker import HoldExpiryWorker
from .waitlist_worker import WaitlistWorker

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages background workers for the application.
    
    Coordinates starting, stopping, and monitoring of all background workers.
    """
    
    def __init__(self):
        """Initialize the worker manager."""
        self.workers: Dict[str, BaseWorker] = {}
        self._setup_workers()
        
    def _setup_workers(self) -> None:
        """Initialize all workers."""
        # Hold expiry worker - runs every 60 seconds
        self.workers["hold_expiry"] = HoldExpiryWorker(interval_seconds=60)
        
        # Waitlist worker - runs every 30 seconds
        self.workers["waitlist"] = WaitlistWorker(interval_seconds=30)
        
        logger.info(f"Initialized {len(self.workers)} workers")
    
    async def start_all(self) -> None:
        """Start all workers."""
        logger.info("Starting all workers")
        
        tasks = []
        for name, worker in self.workers.items():
            try:
                await worker.start()
                logger.info(f"Started worker: {name}")
            except Exception as e:
                logger.error(f"Failed to start worker {name}: {str(e)}", exc_info=True)
        
        logger.info(f"Started {len(self.workers)} workers")
    
    async def stop_all(self) -> None:
        """Stop all workers gracefully."""
        logger.info("Stopping all workers")
        
        tasks = []
        for name, worker in self.workers.items():
            tasks.append(worker.stop())
        
        # Wait for all workers to stop
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any errors
        for i, (name, result) in enumerate(zip(self.workers.keys(), results)):
            if isinstance(result, Exception):
                logger.error(f"Error stopping worker {name}: {str(result)}")
            else:
                logger.info(f"Stopped worker: {name}")
        
        logger.info("All workers stopped")
    
    def get_worker(self, name: str) -> BaseWorker:
        """
        Get a specific worker by name.
        
        Args:
            name: Worker name
            
        Returns:
            The worker instance
            
        Raises:
            KeyError: If worker not found
        """
        return self.workers[name]
    
    def get_worker_status(self) -> Dict[str, bool]:
        """
        Get the status of all workers.
        
        Returns:
            Dictionary mapping worker names to their running status
        """
        return {
            name: worker._running 
            for name, worker in self.workers.items()
        }


# Global worker manager instance
worker_manager = WorkerManager()