from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExperienceLevel, JobType
from app.models.tables import job_skill


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recruiter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    experience_level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    recruiter = relationship("User", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    # When a job is deleted, cascade deletes its applications to avoid FK constraint errors
    applications = relationship("Application", back_populates="job", cascade="all, delete")
    skills = relationship("Skill", secondary=job_skill, back_populates="jobs")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete")
