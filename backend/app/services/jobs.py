"""In-memory optimisation job store.

The proposal dispatches NSGA-II as a FastAPI background task and has the client
poll for results (from sequence diagram). This store tracks job state
in process memory, which is sufficient for a single-instance deployment. For a
horizontally-scaled production deployment this would be swapped for Redis or a
database-backed queue (e.g. Celery/RQ) without changing the API surface.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.schemas.formulation import JobResult, JobState, ParetoPoint


@dataclass
class Job:
    job_id: str
    flock_id: int
    state: JobState = JobState.pending
    error: str | None = None
    nsga2_front: list[ParetoPoint] = field(default_factory=list)
    lp_solution: ParetoPoint | None = None

    def to_result(self) -> JobResult:
        return JobResult(
            job_id=self.job_id,
            flock_id=self.flock_id,
            state=self.state,
            error=self.error,
            nsga2_front=self.nsga2_front,
            lp_solution=self.lp_solution,
        )


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str, flock_id: int) -> Job:
        async with self._lock:
            job = Job(job_id=job_id, flock_id=flock_id)
            self._jobs[job_id] = job
            return job

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, job_id: str, **changes) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)


job_store = JobStore()
