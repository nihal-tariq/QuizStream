from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import DateTime
from app.db import Base
import uuid
import enum


class UserRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

class SignupRequest(Base):
    __tablename__ = "signup_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
