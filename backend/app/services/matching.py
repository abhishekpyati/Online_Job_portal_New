from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import ApplicantProfile, Job


def calculate_match_score(resume_text: str | None, job: Job) -> float:
    job_text = build_job_text(job)
    if not resume_text or not resume_text.strip() or not job_text.strip():
        return 0.0
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([resume_text, job_text])
    score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return round(float(score) * 100, 2)


def build_profile_text(profile: ApplicantProfile | None) -> str:
    if not profile:
        return ""
    skill_text = " ".join(skill.name for skill in profile.skills)
    return " ".join(
        value or ""
        for value in [profile.headline, profile.summary, profile.education, profile.experience, profile.resume_text, skill_text]
    )


def build_job_text(job: Job) -> str:
    skill_text = " ".join(skill.name for skill in job.skills)
    return " ".join([job.title, job.description, job.location, job.job_type.value, job.experience_level.value, skill_text])
