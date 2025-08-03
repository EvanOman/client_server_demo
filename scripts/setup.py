#!/usr/bin/env python3
"""Setup script for the tour booking API."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the server directory to the Python path
server_dir = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_dir))

from alembic import command
from alembic.config import Config
from app.core.database import init_db
from app.models import *  # Import all models to ensure they're registered

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database():
    """Setup the database with initial schema."""
    logger.info("Setting up database...")
    
    try:
        # Initialize database connection
        await init_db()
        logger.info("Database connection initialized")
        
        # Run Alembic migrations
        alembic_cfg = Config(str(server_dir / "db" / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(server_dir / "db" / "alembic"))
        
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed")
        
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise


async def create_sample_data():
    """Create some sample data for testing."""
    from app.core.database import get_async_session
    from app.models.tour import Tour
    from app.models.departure import Departure
    from datetime import datetime, timedelta
    
    logger.info("Creating sample data...")
    
    async with get_async_session() as db:
        try:
            # Check if sample data already exists
            existing_tours = await db.execute("SELECT COUNT(*) FROM tours")
            if existing_tours.scalar() > 0:
                logger.info("Sample data already exists, skipping...")
                return
            
            # Create sample tour
            tour = Tour(
                name="Northern Lights Adventure",
                slug="northern-lights-adventure",
                description="Experience the magical Aurora Borealis in Iceland with expert guides"
            )
            db.add(tour)
            await db.flush()  # Get the tour ID
            
            # Create sample departures
            base_date = datetime.utcnow() + timedelta(days=30)
            for i in range(5):
                departure_date = base_date + timedelta(days=i * 7)
                departure = Departure(
                    tour_id=tour.id,
                    starts_at=departure_date,
                    capacity_total=40,
                    capacity_available=40,
                    price_amount=29999,  # $299.99
                    price_currency="USD"
                )
                db.add(departure)
            
            await db.commit()
            logger.info("Sample data created successfully!")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create sample data: {e}")
            raise


async def main():
    """Main setup function."""
    logger.info("Starting tour booking API setup...")
    
    # Setup database
    await setup_database()
    
    # Create sample data
    await create_sample_data()
    
    logger.info("Setup completed successfully!")
    logger.info("You can now start the API server with: cd server && uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())