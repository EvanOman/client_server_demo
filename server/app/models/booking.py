"""Booking and Hold model definitions."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .departure import Departure


class HoldStatus(str, Enum):
    """Hold status enumeration."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"


class BookingStatus(str, Enum):
    """Booking status enumeration."""
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"


class Hold(Base):
    """Hold entity representing a temporary seat reservation."""
    
    __tablename__ = "holds"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign key to departure
    departure_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("departures.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Hold details
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[HoldStatus] = mapped_column(
        String(20),
        nullable=False,
        default=HoldStatus.ACTIVE,
        index=True
    )
    
    # Idempotency key for this hold
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
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
        CheckConstraint("seats > 0", name="ck_hold_seats_positive"),
        CheckConstraint("seats <= 10", name="ck_hold_seats_max"),
        CheckConstraint("length(customer_ref) > 0", name="ck_hold_customer_ref_not_empty"),
        CheckConstraint("length(idempotency_key) > 0", name="ck_hold_idempotency_key_not_empty"),
    )
    
    # Relationships
    departure: Mapped["Departure"] = relationship("Departure", back_populates="holds")
    booking: Mapped["Booking | None"] = relationship(
        "Booking",
        back_populates="hold",
        cascade="all, delete-orphan",
        uselist=False
    )
    
    def __repr__(self) -> str:
        return (
            f"<Hold(id={self.id}, departure_id={self.departure_id}, "
            f"seats={self.seats}, status={self.status}, expires_at={self.expires_at})>"
        )


class Booking(Base):
    """Booking entity representing a confirmed seat reservation."""
    
    __tablename__ = "bookings"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign key to hold
    hold_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("holds.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Foreign key to departure (denormalized for easier queries)
    departure_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("departures.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Booking details
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[BookingStatus] = mapped_column(
        String(20),
        nullable=False,
        default=BookingStatus.CONFIRMED,
        index=True
    )
    
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
        CheckConstraint("seats > 0", name="ck_booking_seats_positive"),
        CheckConstraint("length(customer_ref) > 0", name="ck_booking_customer_ref_not_empty"),
        CheckConstraint("length(code) > 0", name="ck_booking_code_not_empty"),
    )
    
    # Relationships
    hold: Mapped["Hold"] = relationship("Hold", back_populates="booking")
    departure: Mapped["Departure"] = relationship("Departure", back_populates="bookings")
    
    def __repr__(self) -> str:
        return (
            f"<Booking(id={self.id}, code='{self.code}', hold_id={self.hold_id}, "
            f"seats={self.seats}, status={self.status})>"
        )