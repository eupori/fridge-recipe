from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


# --- SQLAlchemy ORM ---


class JobRecord(Base):
    __tablename__ = "jobs"

    job_id = Column(String(30), primary_key=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Integer, default=0)
    recommendation_id = Column(String(30), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)


# --- Pydantic response schema ---


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = 0
    recommendation_id: str | None = None
    error: str | None = None
    created_at: datetime
