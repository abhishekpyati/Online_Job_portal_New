from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ExperienceLevel, JobType
from app.schemas.common import ORMModel
from app.schemas.profiles import CompanyRead, SkillRead


class JobBase(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=3)
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    job_type: JobType
    experience_level: ExperienceLevel
    company_id: int | None = None
    skills: list[str] = []


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    job_type: JobType | None = None
    experience_level: ExperienceLevel | None = None
    company_id: int | None = None
    skills: list[str] | None = None
    is_active: bool | None = None


class JobRead(ORMModel):
    id: int
    recruiter_id: int
    company_id: int | None
    title: str
    description: str
    location: str
    salary_min: int | None
    salary_max: int | None
    job_type: JobType
    experience_level: ExperienceLevel
    is_active: bool
    created_at: datetime
    skills: list[SkillRead]
    company: CompanyRead | None = None
