from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    applicant_profile = relationship("ApplicantProfile", back_populates="user", uselist=False, cascade="all, delete")
    companies = relationship("Company", back_populates="recruiter", cascade="all, delete")
    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete")
    applications = relationship("Application", back_populates="applicant", cascade="all, delete")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete")
    saved_jobs = relationship("SavedJob", back_populates="user", cascade="all, delete")
