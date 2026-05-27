from pydantic import BaseModel

from app.schemas.applications import ApplicationRead
from app.schemas.jobs import JobRead


class MatchCandidate(BaseModel):
    application: ApplicationRead
    score: float


class RecommendedJob(BaseModel):
    job: JobRead
    score: float
