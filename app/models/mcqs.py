import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app.db import Base

class MCQ(Base):
    __tablename__ = "mcqs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_title = Column(String, nullable=False)  # Title of the video
    question = Column(String, nullable=False)    # Question text
    options = Column(JSONB, nullable=True)       # List of options (for MCQs)
    answer = Column(String, nullable=False)      # Correct answer (text or 'True'/'False')
    created_at = Column(DateTime, default=datetime.utcnow)
