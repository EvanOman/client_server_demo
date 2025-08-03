"""Tour model definition."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from ..core.database import Base

if TYPE_CHECKING:
    from .departure import Departure


class Tour(Base):
    """Tour entity representing a tour offering."""
    
    __tablename__ = "tours"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Tour information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
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
    
    # Relationships
    departures: Mapped[list["Departure"]] = relationship(
        "Departure",
        back_populates="tour",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Tour(id={self.id}, name='{self.name}', slug='{self.slug}')>"