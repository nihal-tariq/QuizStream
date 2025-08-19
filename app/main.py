"""
Main FastAPI application entry point.
Initializes the database, sets up routes, and configures authentication.
"""

from fastapi import Depends, FastAPI

from app.auth import require_role
from app.db import Base, engine
from app.models import mcqs, user, video
from app.routers import (
    auth_router,
    chatbot_router,
    delete_mcqs,
    manage_users,
    quiz,
    take_quiz,
    video_approve,
    video_list,
    video_upload,
)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    """Initialize database tables on application startup."""
    Base.metadata.create_all(bind=engine)


# Authentication routes
app.include_router(auth_router.router, tags=["Auth"])
app.include_router(manage_users.router)

# Teacher-only routes
teacher_dependencies = [Depends(require_role(["teacher"]))]

app.include_router(video_upload.router, dependencies=teacher_dependencies)
app.include_router(video_list.router, dependencies=teacher_dependencies)
app.include_router(video_approve.router, dependencies=teacher_dependencies)
app.include_router(quiz.router, dependencies=teacher_dependencies)
app.include_router(delete_mcqs.router, dependencies=teacher_dependencies)

# Routes accessible by both teachers and students
teacher_student_dependencies = [Depends(require_role(["teacher", "student"]))]

app.include_router(chatbot_router.router, dependencies=teacher_student_dependencies)
app.include_router(take_quiz.router, dependencies=teacher_student_dependencies)
