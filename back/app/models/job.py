from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = 0
    recommendation_id: str | None = None
    error: str | None = None
    created_at: datetime
