from pydantic import BaseModel

from app.schemas.common import ORMModel


class SkillRead(ORMModel):
    id: int
    name: str


class ApplicantProfileBase(BaseModel):
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    education: str | None = None
    experience: str | None = None
    skills: list[str] = []


class ApplicantProfileUpsert(ApplicantProfileBase):
    pass


class ApplicantProfileRead(ORMModel):
    id: int
    user_id: int
    phone: str | None
    location: str | None
    headline: str | None
    summary: str | None
    education: str | None
    experience: str | None
    resume_path: str | None
    profile_image_path: str | None
    completion_percentage: int
    skills: list[SkillRead]


class CompanyBase(BaseModel):
    name: str
    website: str | None = None
    location: str | None = None
    description: str | None = None


class CompanyRead(ORMModel):
    id: int
    recruiter_id: int
    name: str
    website: str | None
    location: str | None
    description: str | None
