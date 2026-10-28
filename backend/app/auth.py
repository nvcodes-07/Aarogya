import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Optional, Dict, Any, Set
from fastapi import Header, HTTPException, status
from app.config import settings

# In-memory registry of revoked operator session tokens
REVOKED_TOKENS: Set[str] = set()

def revoke_operator_token(token: str) -> None:
    """Add a token to the revoked tokens registry."""
    if token:
        clean_token = token.replace("Bearer ", "").strip()
        REVOKED_TOKENS.add(clean_token)

def is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    return clean_token in REVOKED_TOKENS

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))

def create_operator_token(username: str) -> Dict[str, Any]:
    """Generate a signed HMAC-SHA256 operator session token."""
    now = int(time.time())
    expires_at = now + (settings.OPERATOR_TOKEN_EXPIRE_HOURS * 3600)
    
    payload = {
        "jti": uuid.uuid4().hex,
        "sub": username,
        "role": "hospital_operator",
        "iat": now,
        "exp": expires_at,
        "hospital": settings.HOSPITAL_NAME
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    payload_b64 = _b64_encode(payload_bytes)
    
    signature = hmac.new(
        settings.OPERATOR_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    token = f"{payload_b64}.{signature}"
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "username": username,
        "role": "hospital_operator"
    }

def verify_operator_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify an operator token's HMAC signature and expiration."""
    if not token or "." not in token:
        return None
        
    if is_token_revoked(token):
        return None

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
            
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            settings.OPERATOR_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
            
        # Parse payload
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # Check expiration
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None
            
        if payload.get("role") != "hospital_operator":
            return None
            
        return payload
    except Exception:
        return None

def require_operator(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """FastAPI Dependency: Enforces operator authorization on protected dashboard endpoints."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hospital operator authorization required. Please authenticate via the operator portal.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    token = authorization[7:].strip()
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operator session has been logged out and invalidated. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    operator_info = verify_operator_token(token)
    if not operator_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired operator session token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    operator_info["token"] = token
    return operator_info

