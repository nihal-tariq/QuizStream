from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.user import User, SignupRequest, UserRole
from app.utils.get_db import get_db
from app.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()


@router.post("/signup")
def signup(username: str, name: str, password: str, role: UserRole, db: Session = Depends(get_db)):
    # Check if username already exists in either table
    if db.query(User).filter(User.username == username).first() or \
       db.query(SignupRequest).filter(SignupRequest.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(password)
    signup_request = SignupRequest(
        username=username,
        name=name,
        password_hash=hashed_password,
        role=role
    )
    db.add(signup_request)
    db.commit()
    db.refresh(signup_request)
    return {"id": str(signup_request.id), "message": "Signup request submitted", "status": signup_request.status}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}
