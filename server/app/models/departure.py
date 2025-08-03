"""Departure model definition."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .booking import Booking, Hold
    from .inventory import InventoryAdjustment
    from .tour import Tour
    from .waitlist import WaitlistEntry


class Departure(Base):
    """Departure entity representing a specific tour departure."""
    
    __tablename__ = "departures"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign key to tour
    tour_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tours.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Departure details
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    capacity_total: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Price information (stored as minor units, e.g., cents)
    price_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now()
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("capacity_total >= 0", name="ck_departure_capacity_total_non_negative"),
        CheckConstraint("capacity_available >= 0", name="ck_departure_capacity_available_non_negative"),
        CheckConstraint("capacity_available <= capacity_total", name="ck_departure_capacity_available_lte_total"),
        CheckConstraint("price_amount >= 0", name="ck_departure_price_amount_non_negative"),
        CheckConstraint("length(price_currency) = 3", name="ck_departure_price_currency_length"),
    )
    
    # Relationships
    tour: Mapped["Tour"] = relationship("Tour", back_populates="departures")
    holds: Mapped[list["Hold"]] = relationship(
        "Hold",
        back_populates="departure",
        cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="departure",
        cascade="all, delete-orphan"
    )
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(
        "WaitlistEntry",
        back_populates="departure",
        cascade="all, delete-orphan"
    )
    inventory_adjustments: Mapped[list["InventoryAdjustment"]] = relationship(
        "InventoryAdjustment",
        back_populates="departure",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Departure(id={self.id}, tour_id={self.tour_id}, "
            f"starts_at={self.starts_at}, capacity={self.capacity_available}/{self.capacity_total})>"
        )