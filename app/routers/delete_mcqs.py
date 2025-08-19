"""
MCQ Management Router.

This module provides an endpoint to delete a specific MCQ by ID.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.mcqs import MCQ
from app.utils.get_db import get_db


# Router instance
router = APIRouter(prefix="/mcqs", tags=["Manage MCQs"])


# ---------- Pydantic Schemas ---------- #
class DeleteResponseSchema(BaseModel):
    """Schema for delete response."""
    message: str


# ---------- Routes ---------- #
@router.delete("/{mcq_id}", summary="Delete MCQ by ID", response_model=DeleteResponseSchema)
def delete_mcq(mcq_id: UUID, db: Session = Depends(get_db)) -> DeleteResponseSchema:
    """
    Delete a specific MCQ by ID.

    Args:
        mcq_id (UUID): The unique ID of the MCQ to delete.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If MCQ with given ID does not exist.

    Returns:
        DeleteResponseSchema: Confirmation message.
    """
    # Find MCQ by ID
    mcq = db.query(MCQ).filter(MCQ.id == mcq_id).first()
    if not mcq:
        raise HTTPException(status_code=404, detail="MCQ not found")

    # Delete the MCQ
    db.delete(mcq)
    db.commit()

    return {"message": f"MCQ with ID {mcq_id} has been deleted successfully"}
