"""
Authentication and authorization utilities.
Handles JWT token generation, validation, and role-based access control.
"""
import os

from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class TokenData(BaseModel):
    """Schema for storing user claims from JWT."""
    username: str
    role: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token.

    Args:
        data (dict): Payload data to encode.
        expires_delta (Optional[timedelta]): Expiration delta for the token.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Extract and validate the current user from the JWT token.

    Args:
        token (str): JWT token provided by OAuth2 scheme.

    Returns:
        TokenData: Decoded token data containing username and role.

    Raises:
        HTTPException: If token is invalid or missing required claims.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception


def require_role(allowed_roles: list[str]):
    """
    Dependency for enforcing role-based access.

    Args:
        allowed_roles (list[str]): Roles allowed to access the resource.

    Returns:
        Callable: A dependency function that checks the user's role.
    """
    def role_checker(user: TokenData = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    return role_checker
