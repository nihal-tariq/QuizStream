# app/routers/chatbot_router.py

from fastapi import APIRouter, Form
from pydantic import BaseModel
from typing import List, Dict
from app.services.chatbot import chat_with_video

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# In-memory session storage
chat_sessions: Dict[str, List[Dict[str, str]]] = {}


class ChatResponse(BaseModel):
    response: str


@router.post("/ask", response_model=ChatResponse)
def chat_endpoint(
    video_title: str = Form(..., description="Title of the video you want to query"),
    user_query: str = Form(..., description="Your question about the video"),
    session_id: str = Form(..., description="Unique session ID to maintain conversation history")
):
    # Ensure history exists
    history = chat_sessions.setdefault(session_id, [])

    # Call chat service
    reply = chat_with_video(video_title, user_query, history)

    # Persist exchange
    history.append({"user": user_query, "bot": reply})

    return ChatResponse(response=reply)
