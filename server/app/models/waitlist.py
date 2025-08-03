"""Waitlist model definition."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .departure import Departure


class WaitlistEntry(Base):
    """Waitlist entry for a departure when capacity is full."""

    __tablename__ = "waitlist_entries"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )

    # Foreign key to departure
    departure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departures.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Waitlist details
    customer_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        index=True  # Index for ordering by creation time
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("length(customer_ref) > 0", name="ck_waitlist_customer_ref_not_empty"),
        # Unique constraint to prevent same customer from joining waitlist multiple times
        # for the same departure
        {"schema": None}  # This will be replaced with proper unique constraint
    )

    # Add unique constraint programmatically
    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        CheckConstraint("length(customer_ref) > 0", name="ck_waitlist_customer_ref_not_empty"),
        UniqueConstraint("departure_id", "customer_ref", name="uq_waitlist_departure_customer"),
    )

    # Relationships
    departure: Mapped["Departure"] = relationship("Departure", back_populates="waitlist_entries")

    def __repr__(self) -> str:
        return (
            f"<WaitlistEntry(id={self.id}, departure_id={self.departure_id}, "
            f"customer_ref='{self.customer_ref}', created_at={self.created_at}, "
            f"notified_at={self.notified_at})>"
        )
