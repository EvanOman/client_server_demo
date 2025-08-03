"""Idempotency service for handling duplicate requests."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import ProblemDetailsException
from ..models.idempotency import IdempotencyRecord

logger = logging.getLogger(__name__)


class IdempotencyMismatchError(ProblemDetailsException):
    """Exception when idempotency key is reused with different request body."""

    def __init__(self, idempotency_key: str, method: str):
        super().__init__(
            status_code=422,
            title="Idempotency Key Mismatch",
            detail=f"Idempotency key '{idempotency_key}' was already used for method '{method}' with different request body",
            type_uri="https://example.com/problems/idempotency-key-mismatch",
            extensions={
                "code": "IDEMPOTENCY_KEY_MISMATCH",
                "retryable": False,
                "idempotency_key": idempotency_key,
                "method": method,
            },
        )


class IdempotencyService:
    """Service for handling idempotent operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _compute_request_hash(self, request_body: dict[str, Any]) -> str:
        """Compute SHA-256 hash of normalized request body."""
        # Sort keys recursively to ensure consistent hash
        normalized = json.dumps(request_body, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    async def check_idempotency(
        self,
        idempotency_key: str,
        method: str,
        request_body: dict[str, Any],
        ttl_hours: int = 24
    ) -> tuple[int, dict[str, Any], dict[str, str] | None] | None:
        """
        Check if request is idempotent and return cached response if available.

        Args:
            idempotency_key: Unique idempotency key
            method: HTTP method/operation name
            request_body: Request body to hash and compare
            ttl_hours: TTL for idempotency records in hours

        Returns:
            Tuple of (status_code, response_body, headers) if cached response exists,
            None if this is a new request

        Raises:
            IdempotencyMismatchError: If key exists with different request body
        """
        request_hash = self._compute_request_hash(request_body)

        # Query for existing record
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.method == method,
            IdempotencyRecord.expires_at > datetime.utcnow()
        )

        result = await self.db.execute(stmt)
        existing_record = result.scalar_one_or_none()

        if existing_record is None:
            # No existing record, this is a new request
            logger.info(
                "No existing idempotency record found",
                extra={
                    "idempotency_key": idempotency_key,
                    "method": method,
                    "request_hash": request_hash[:8]  # First 8 chars for logging
                }
            )
            return None

        # Check if request body matches
        if existing_record.request_body_hash != request_hash:
            logger.warning(
                "Idempotency key mismatch",
                extra={
                    "idempotency_key": idempotency_key,
                    "method": method,
                    "existing_hash": existing_record.request_body_hash[:8],
                    "new_hash": request_hash[:8]
                }
            )
            raise IdempotencyMismatchError(idempotency_key, method)

        # Return cached response
        logger.info(
            "Returning cached idempotent response",
            extra={
                "idempotency_key": idempotency_key,
                "method": method,
                "status_code": existing_record.response_status_code,
                "created_at": existing_record.created_at.isoformat()
            }
        )

        response_headers = None
        if existing_record.response_headers:
            try:
                response_headers = json.loads(existing_record.response_headers)
            except json.JSONDecodeError:
                logger.warning(
                    "Failed to decode response headers from idempotency record",
                    extra={"idempotency_key": idempotency_key, "method": method}
                )

        response_body = json.loads(existing_record.response_body)

        return (
            existing_record.response_status_code,
            response_body,
            response_headers
        )

    async def store_response(
        self,
        idempotency_key: str,
        method: str,
        request_body: dict[str, Any],
        status_code: int,
        response_body: dict[str, Any],
        response_headers: dict[str, str] | None = None,
        ttl_hours: int = 24
    ) -> None:
        """
        Store response for idempotent operation.

        Args:
            idempotency_key: Unique idempotency key
            method: HTTP method/operation name
            request_body: Original request body
            status_code: Response status code
            response_body: Response body to cache
            response_headers: Response headers to cache
            ttl_hours: TTL for idempotency record in hours
        """
        request_hash = self._compute_request_hash(request_body)
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        # Serialize response data
        response_body_json = json.dumps(response_body, sort_keys=True, separators=(',', ':'))
        response_headers_json = None
        if response_headers:
            response_headers_json = json.dumps(response_headers, sort_keys=True, separators=(',', ':'))

        # Create idempotency record
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            method=method,
            request_body_hash=request_hash,
            response_status_code=status_code,
            response_body=response_body_json,
            response_headers=response_headers_json,
            expires_at=expires_at
        )

        try:
            self.db.add(record)
            await self.db.commit()

            logger.info(
                "Stored idempotency record",
                extra={
                    "idempotency_key": idempotency_key,
                    "method": method,
                    "status_code": status_code,
                    "expires_at": expires_at.isoformat()
                }
            )

        except IntegrityError as e:
            # Another request might have stored the same key+method combination
            # This is fine, just log and continue
            await self.db.rollback()
            logger.info(
                "Idempotency record already exists (race condition)",
                extra={
                    "idempotency_key": idempotency_key,
                    "method": method,
                    "error": str(e)
                }
            )

    async def cleanup_expired_records(self, batch_size: int = 1000) -> int:
        """
        Clean up expired idempotency records.

        Args:
            batch_size: Number of records to delete in one batch

        Returns:
            Number of records deleted
        """
        from sqlalchemy import delete

        stmt = delete(IdempotencyRecord).where(
            IdempotencyRecord.expires_at <= datetime.utcnow()
        )

        result = await self.db.execute(stmt)
        deleted_count = result.rowcount

        await self.db.commit()

        if deleted_count > 0:
            logger.info(
                "Cleaned up expired idempotency records",
                extra={"deleted_count": deleted_count}
            )

        return deleted_count
