"""Inventory adjustment model definition."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .departure import Departure


class InventoryAdjustment(Base):
    """Inventory adjustment record for audit trail of capacity changes."""

    __tablename__ = "inventory_adjustments"

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

    # Adjustment details
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # Can be positive or negative
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # Who made the adjustment

    # Previous and new values for audit trail
    capacity_total_before: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_total_after: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_available_before: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_available_after: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        index=True  # Index for audit queries
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("delta != 0", name="ck_inventory_adjustment_delta_nonzero"),
        CheckConstraint("length(reason) > 0", name="ck_inventory_adjustment_reason_not_empty"),
        CheckConstraint("length(actor) > 0", name="ck_inventory_adjustment_actor_not_empty"),
        CheckConstraint("capacity_total_before >= 0", name="ck_inventory_adjustment_total_before_non_negative"),
        CheckConstraint("capacity_total_after >= 0", name="ck_inventory_adjustment_total_after_non_negative"),
        CheckConstraint("capacity_available_before >= 0", name="ck_inventory_adjustment_available_before_non_negative"),
        CheckConstraint("capacity_available_after >= 0", name="ck_inventory_adjustment_available_after_non_negative"),
        CheckConstraint(
            "capacity_available_before <= capacity_total_before",
            name="ck_inventory_adjustment_available_lte_total_before"
        ),
        CheckConstraint(
            "capacity_available_after <= capacity_total_after",
            name="ck_inventory_adjustment_available_lte_total_after"
        ),
        CheckConstraint(
            "capacity_total_after = capacity_total_before + delta",
            name="ck_inventory_adjustment_total_delta_consistency"
        ),
    )

    # Relationships
    departure: Mapped["Departure"] = relationship("Departure", back_populates="inventory_adjustments")

    def __repr__(self) -> str:
        return (
            f"<InventoryAdjustment(id={self.id}, departure_id={self.departure_id}, "
            f"delta={self.delta}, actor='{self.actor}', created_at={self.created_at})>"
        )
