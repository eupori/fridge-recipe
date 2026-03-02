from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.job import JobRecord, JobStatus

logger = logging.getLogger(__name__)


def create_job() -> str:
    job_id = f"job_{uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        record = JobRecord(
            job_id=job_id, status="pending", progress=0, created_at=datetime.now(UTC)
        )
        db.add(record)
        db.commit()
    finally:
        db.close()
    _cleanup_old_jobs()
    return job_id


def get_job(job_id: str) -> JobStatus | None:
    db = SessionLocal()
    try:
        record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
        if record is None:
            return None
        return JobStatus(
            job_id=record.job_id,
            status=record.status,
            progress=record.progress,
            recommendation_id=record.recommendation_id,
            error=record.error,
            created_at=record.created_at,
        )
    finally:
        db.close()


def update_job(job_id: str, **kwargs: object) -> None:
    db = SessionLocal()
    try:
        record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
        if record is None:
            return
        for key, value in kwargs.items():
            setattr(record, key, value)
        db.commit()
    finally:
        db.close()


def _cleanup_old_jobs() -> None:
    db = SessionLocal()
    try:
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        count = db.query(JobRecord).filter(JobRecord.created_at < cutoff).delete()
        db.commit()
        if count:
            logger.info(f"만료된 Job {count}개 정리")
    finally:
        db.close()
