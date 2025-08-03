"""FastAPI dependencies for database, authentication, and idempotency."""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt import PyJWTError
import hashlib
import time
from datetime import datetime, timedelta

from .database import get_async_session
from .config import settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database dependency that provides async database sessions.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in get_async_session():
        yield session


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> dict:
    """
    Authentication dependency that validates Bearer tokens.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        dict: User information from validated token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.bearer_token_secret,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return {
            "user_id": user_id,
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
        }
        
    except PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# In-memory cache for idempotency keys (in production, use Redis)
_idempotency_cache: dict[str, dict] = {}


def _cleanup_expired_keys() -> None:
    """Remove expired idempotency keys from cache."""
    current_time = time.time()
    expired_keys = [
        key for key, data in _idempotency_cache.items()
        if current_time - data["timestamp"] > settings.idempotency_ttl_seconds
    ]
    for key in expired_keys:
        del _idempotency_cache[key]


async def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
) -> Optional[str]:
    """
    Extract and validate idempotency key from request headers.
    
    Args:
        idempotency_key: Idempotency key from header
        
    Returns:
        str: Validated idempotency key or None if not provided
        
    Raises:
        HTTPException: If idempotency key format is invalid
    """
    if not idempotency_key:
        return None
    
    # Clean up expired keys periodically
    _cleanup_expired_keys()
    
    # Validate key length and format
    if len(idempotency_key) < 1 or len(idempotency_key) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency key must be between 1 and 255 characters"
        )
    
    # Generate a hash of the key for consistent storage
    key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
    
    return key_hash


async def check_idempotency(
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> Optional[dict]:
    """
    Check if request with idempotency key has been processed before.
    
    Args:
        idempotency_key: Hashed idempotency key
        
    Returns:
        dict: Previous response if found, None otherwise
    """
    if not idempotency_key:
        return None
    
    cached_response = _idempotency_cache.get(idempotency_key)
    if cached_response:
        current_time = time.time()
        if current_time - cached_response["timestamp"] <= settings.idempotency_ttl_seconds:
            return cached_response["response"]
        else:
            # Remove expired entry
            del _idempotency_cache[idempotency_key]
    
    return None


async def store_idempotent_response(
    response_data: dict,
    idempotency_key: Optional[str] = None
) -> None:
    """
    Store response for idempotency key.
    
    Args:
        response_data: Response data to cache
        idempotency_key: Hashed idempotency key
    """
    if not idempotency_key:
        return
    
    # Implement cache size limit
    if len(_idempotency_cache) >= settings.idempotency_cache_size:
        # Remove oldest entry (simple FIFO)
        oldest_key = min(
            _idempotency_cache.keys(),
            key=lambda k: _idempotency_cache[k]["timestamp"]
        )
        del _idempotency_cache[oldest_key]
    
    _idempotency_cache[idempotency_key] = {
        "response": response_data,
        "timestamp": time.time()
    }


# Optional dependency for authenticated users
OptionalAuth = lambda: Depends(get_current_user)
RequiredAuth = Depends(get_current_user)
DatabaseSession = Depends(get_db)
IdempotencyKey = Depends(get_idempotency_key)
IdempotencyCheck = Depends(check_idempotency)