from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Application, ApplicantProfile, Job, User, UserRole
from app.schemas.matching import MatchCandidate, RecommendedJob
from app.services.matching import build_profile_text, calculate_match_score

router = APIRouter(prefix="/matching", tags=["Resume Matching"])


@router.get("/recommended-jobs", response_model=list[RecommendedJob])
def recommended_jobs(
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> list[RecommendedJob]:
    profile = db.query(ApplicantProfile).options(selectinload(ApplicantProfile.skills)).filter(ApplicantProfile.user_id == current_user.id).first()
    profile_text = build_profile_text(profile)
    jobs = db.query(Job).options(selectinload(Job.skills), selectinload(Job.company)).filter(Job.is_active.is_(True)).all()
    ranked = [{"job": job, "score": calculate_match_score(profile_text, job)} for job in jobs]
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:10]


@router.get("/jobs/{job_id}/candidates", response_model=list[MatchCandidate])
def top_candidates(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> list[MatchCandidate]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can view candidates only for your jobs")
    applications = (
        db.query(Application)
        .options(selectinload(Application.job).selectinload(Job.skills), selectinload(Application.applicant))
        .filter(Application.job_id == job_id)
        .all()
    )
    return sorted([{"application": item, "score": item.match_score} for item in applications], key=lambda item: item["score"], reverse=True)
