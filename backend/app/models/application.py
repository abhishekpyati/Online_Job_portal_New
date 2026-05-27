from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "applicant_id", name="uq_application_job_applicant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.applied, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications")

    @property
    def applicant_profile(self):
        return self.applicant.applicant_profile if self.applicant else None
