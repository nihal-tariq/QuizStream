from fastapi import FastAPI
from fastapi import Depends
from app.db import Base, engine
from app.models import video, mcqs, user
from app.routers import video_upload, chatbot_router, quiz, video_list, video_approve, delete_mcqs, auth_router, manage_users, take_quiz
from app.auth import require_role

app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Auth routes


app.include_router(auth_router.router, tags=["Auth"])
app.include_router(manage_users.router)

# Teacher-only routes
app.include_router(video_upload.router, dependencies=[Depends(require_role(["teacher"]))])
app.include_router(video_list.router, dependencies=[Depends(require_role(["teacher"]))])
app.include_router(video_approve.router, dependencies=[Depends(require_role(["teacher"]))])
app.include_router(quiz.router, dependencies=[Depends(require_role(["teacher"]))])
app.include_router(delete_mcqs.router, dependencies=[Depends(require_role(["teacher"]))])


# Both teacher and student can access
app.include_router(chatbot_router.router, dependencies=[Depends(require_role(["teacher", "student"]))])
app.include_router(take_quiz.router, dependencies=[Depends(require_role(["teacher", "student"]))])