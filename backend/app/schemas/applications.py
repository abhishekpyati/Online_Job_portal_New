from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ApplicationStatus
from app.schemas.common import ORMModel
from app.schemas.jobs import JobRead
from app.schemas.profiles import ApplicantProfileRead
from app.schemas.users import UserRead


class ApplicationCreate(BaseModel):
    job_id: int
    cover_letter: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationRead(ORMModel):
    id: int
    job_id: int
    applicant_id: int
    cover_letter: str | None
    match_score: float
    status: ApplicationStatus
    created_at: datetime
    job: JobRead | None = None
    applicant: UserRead | None = None
    applicant_profile: ApplicantProfileRead | None = None
