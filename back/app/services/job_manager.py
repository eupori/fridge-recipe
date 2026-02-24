from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.job import JobStatus

logger = logging.getLogger(__name__)

_jobs: dict[str, JobStatus] = {}
_MAX_JOBS = 200


def create_job() -> str:
    job_id = f"job_{uuid4().hex[:10]}"
    _jobs[job_id] = JobStatus(
        job_id=job_id, status="pending", created_at=datetime.now(UTC)
    )
    _cleanup_old_jobs()
    return job_id


def get_job(job_id: str) -> JobStatus | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs: object) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return
    _jobs[job_id] = job.model_copy(update=kwargs)


def _cleanup_old_jobs() -> None:
    if len(_jobs) <= _MAX_JOBS:
        return
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    expired = [jid for jid, j in _jobs.items() if j.created_at < cutoff]
    for jid in expired:
        del _jobs[jid]
    logger.info(f"만료된 Job {len(expired)}개 정리 (남은 Job: {len(_jobs)})")
