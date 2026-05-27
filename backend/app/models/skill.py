from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tables import applicant_skill, job_skill


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)

    applicant_profiles = relationship("ApplicantProfile", secondary=applicant_skill, back_populates="skills")
    jobs = relationship("Job", secondary=job_skill, back_populates="skills")
