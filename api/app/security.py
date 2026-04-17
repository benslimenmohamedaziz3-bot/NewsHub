from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from .database import get_db
from .models import User

auth_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> str:
    resolved_salt = salt or urlsafe_b64encode(os.urandom(16)).decode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt.encode("utf-8"), 100_000)
    return f"{resolved_salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, expected_hash = password_hash.split("$", 1)
    candidate_hash = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(auth_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
