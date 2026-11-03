import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_context.verify(password, hashed)


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": expires,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise credentials_error

    return user


def require_roles(*allowed_roles):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission for this action",
            )
        return user

    return role_checker