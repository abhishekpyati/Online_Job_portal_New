from sqlalchemy import Column, ForeignKey, Table

from app.db.base import Base

applicant_skill = Table(
    "applicant_skill",
    Base.metadata,
    Column("profile_id", ForeignKey("applicant_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

job_skill = Table(
    "job_skill",
    Base.metadata,
    Column("job_id", ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)
