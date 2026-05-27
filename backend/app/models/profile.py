from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tables import applicant_skill


class ApplicantProfile(Base):
    __tablename__ = "applicant_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    location: Mapped[str | None] = mapped_column(String(120))
    headline: Mapped[str | None] = mapped_column(String(180))
    summary: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    resume_path: Mapped[str | None] = mapped_column(String(255))
    resume_text: Mapped[str | None] = mapped_column(Text)
    profile_image_path: Mapped[str | None] = mapped_column(String(255))

    user = relationship("User", back_populates="applicant_profile")
    skills = relationship("Skill", secondary=applicant_skill, back_populates="applicant_profiles")

    @property
    def completion_percentage(self) -> int:
        fields = [
            self.phone,
            self.location,
            self.headline,
            self.summary,
            self.education,
            self.experience,
            self.resume_path,
            self.profile_image_path,
            ",".join(skill.name for skill in self.skills),
        ]
        completed = sum(1 for field in fields if field)
        return round((completed / len(fields)) * 100)
