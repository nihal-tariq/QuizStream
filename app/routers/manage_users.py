from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.user import SignupRequest, User
from app.utils.get_db import get_db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/users", tags=["User Management"])

# --- VIEW PENDING REQUESTS ---


@router.get("/requests")
def get_pending_requests(db: Session = Depends(get_db)):
    requests = db.query(SignupRequest).filter(SignupRequest.status == "pending").all()
    return [
        {
            "id": str(req.id),
            "role": req.role.value,
            "username": req.username,
            "name": req.name
        }
        for req in requests
    ]

# --- MANAGE USERS (APPROVE / DECLINE) ---
@router.post("/manage")
def manage_user(request_id: UUID, action: str, db: Session = Depends(get_db)):
    signup_req = db.query(SignupRequest).filter(SignupRequest.id == request_id).first()
    if not signup_req:
        raise HTTPException(status_code=404, detail="Signup request not found")

    if action.upper() == "APPROVE":
        # Create real user
        new_user = User(
            username=signup_req.username,
            name=signup_req.name,
            password_hash=signup_req.password_hash,
            role=signup_req.role
        )
        db.add(new_user)
        db.delete(signup_req)
        db.commit()
        return {"message": f"User {new_user.username} approved and created"}
    elif action.upper() == "DECLINE":
        db.delete(signup_req)
        db.commit()
        return {"message": f"Signup request for {signup_req.username} declined"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use APPROVE or DECLINE.")
