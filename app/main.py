from fastapi import FastAPI
from app.db import Base, engine
from app.models import video
from app.routers import video_upload, chatbot_router

app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# Register the video routes
app.include_router(video_upload.router)
app.include_router(chatbot_router.router)
