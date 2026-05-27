import enum


class UserRole(str, enum.Enum):
    applicant = "applicant"
    recruiter = "recruiter"
    admin = "admin"


class JobType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    remote = "remote"


class ExperienceLevel(str, enum.Enum):
    entry = "entry"
    mid = "mid"
    senior = "senior"
    lead = "lead"


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    shortlisted = "shortlisted"
    rejected = "rejected"
    interview_scheduled = "interview_scheduled"
