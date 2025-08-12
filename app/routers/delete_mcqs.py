from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.mcqs import MCQ
from uuid import UUID
from app.utils.get_db import get_db

router = APIRouter()

# Dependency to get DB session
get_db()

@router.delete("/mcqs/{mcq_id}", summary="Delete MCQ by ID")
def delete_mcq(mcq_id: UUID, db: Session = Depends(get_db)):
    # Find MCQ by ID
    mcq = db.query(MCQ).filter(MCQ.id == mcq_id).first()
    if not mcq:
        raise HTTPException(status_code=404, detail="MCQ not found")

    # Delete the MCQ
    db.delete(mcq)
    db.commit()

    return {"message": f"MCQ with ID {mcq_id} has been deleted successfully"}
