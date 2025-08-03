"""Idempotency record model definition."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class IdempotencyRecord(Base):
    """Idempotency record for tracking duplicate requests."""
    
    __tablename__ = "idempotency_records"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid()
    )
    
    # Idempotency key and method combination
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Request body hash for validation
    request_body_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    
    # Response information
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    response_headers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    
    # TTL information
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True  # Index for cleanup queries
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
        CheckConstraint("length(idempotency_key) > 0", name="ck_idempotency_key_not_empty"),
        CheckConstraint("length(method) > 0", name="ck_idempotency_method_not_empty"),
        CheckConstraint("length(request_body_hash) = 64", name="ck_idempotency_hash_length"),
        CheckConstraint("response_status_code >= 100", name="ck_idempotency_status_code_valid"),
        CheckConstraint("response_status_code <= 599", name="ck_idempotency_status_code_max"),
        # Unique constraint for idempotency key + method combination
        # This ensures we can only have one record per key+method combination
        {"postgresql_where": "expires_at > now()"}  # Only enforce uniqueness for non-expired records
    )
    
    # Add unique constraint programmatically
    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        CheckConstraint("length(idempotency_key) > 0", name="ck_idempotency_key_not_empty"),
        CheckConstraint("length(method) > 0", name="ck_idempotency_method_not_empty"),
        CheckConstraint("length(request_body_hash) = 64", name="ck_idempotency_hash_length"),
        CheckConstraint("response_status_code >= 100", name="ck_idempotency_status_code_valid"),
        CheckConstraint("response_status_code <= 599", name="ck_idempotency_status_code_max"),
        UniqueConstraint("idempotency_key", "method", name="uq_idempotency_key_method"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<IdempotencyRecord(id={self.id}, key='{self.idempotency_key}', "
            f"method='{self.method}', status={self.response_status_code}, "
            f"expires_at={self.expires_at})>"
        )