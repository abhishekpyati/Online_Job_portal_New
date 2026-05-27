from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Application, ApplicantProfile, Job, User, UserRole
from app.models.enums import ApplicationStatus
from app.schemas.applications import ApplicationCreate, ApplicationRead, ApplicationStatusUpdate
from app.services.ai_suitability import check_ai_suitability
from app.services.matching import calculate_match_score
from app.services.notifications import create_notification

router = APIRouter(prefix="/applications", tags=["Applications"])


def application_query(db: Session):
    return db.query(Application).options(
        selectinload(Application.job).selectinload(Job.skills),
        selectinload(Application.job).selectinload(Job.company),
        selectinload(Application.applicant).selectinload(User.applicant_profile).selectinload(ApplicantProfile.skills),
    )


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def apply_for_job(
    payload: ApplicationCreate,
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> Application:
    job = db.query(Job).options(selectinload(Job.skills)).filter(Job.id == payload.job_id, Job.is_active.is_(True)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = db.query(ApplicantProfile).options(selectinload(ApplicantProfile.skills)).filter(ApplicantProfile.user_id == current_user.id).first()
    score = calculate_match_score(profile.resume_text if profile else "", job)
    application = Application(job_id=job.id, applicant_id=current_user.id, cover_letter=payload.cover_letter, match_score=score)
    db.add(application)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="You already applied for this job") from exc
    db.refresh(application)
    await create_notification(db, job.recruiter_id, f"{current_user.full_name} applied for {job.title}")
    return application


@router.get("/{application_id}/resume")
def download_resume(
    application_id: int,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> FileResponse:
    application = application_query(db).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can download resumes only for your jobs")
    profile = application.applicant_profile
    if not profile or not profile.resume_path:
        raise HTTPException(status_code=404, detail="Resume not uploaded by applicant")
    resume_path = Path(profile.resume_path)
    if not resume_path.exists():
        raise HTTPException(status_code=404, detail="Resume file is missing")
    return FileResponse(resume_path, filename=resume_path.name)


@router.get("/{application_id}/suitability")
async def check_suitability(
    application_id: int,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> dict:
    application = application_query(db).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can check suitability only for your jobs")
    result = await check_ai_suitability(application)
    return {
        "application_id": application.id,
        "job_title": application.job.title,
        "applicant_name": application.applicant.full_name if application.applicant else "Applicant",
        **result,
    }


@router.get("/me", response_model=list[ApplicationRead])
def my_applications(
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> list[Application]:
    return application_query(db).filter(Application.applicant_id == current_user.id).order_by(Application.created_at.desc()).all()


@router.get("/recruiter", response_model=list[ApplicationRead])
def recruiter_applications(
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> list[Application]:
    return (
        application_query(db)
        .join(Job, Job.id == Application.job_id)
        .filter(Job.recruiter_id == current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )


@router.put("/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> Application:
    application = application_query(db).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can manage only applications for your jobs")
    current_status = application.status.value if hasattr(application.status, "value") else application.status
    requested_status = payload.status.value if hasattr(payload.status, "value") else payload.status
    if current_status == ApplicationStatus.shortlisted.value and requested_status == ApplicationStatus.rejected.value:
        raise HTTPException(status_code=400, detail="Cannot reject an application that has already been shortlisted.")
    if current_status == ApplicationStatus.rejected.value and requested_status == ApplicationStatus.shortlisted.value:
        raise HTTPException(status_code=400, detail="Cannot shortlist an application that has already been rejected.")
    application.status = payload.status
    db.commit()
    db.refresh(application)
    status_messages = {
        "shortlisted": f"You have been shortlisted for {application.job.title}.",
        "rejected": f"You were not shortlisted for {application.job.title}.",
        "interview_scheduled": f"Interview scheduled for your {application.job.title} application.",
        "applied": f"Your application for {application.job.title} is marked as applied.",
    }
    await create_notification(db, application.applicant_id, status_messages.get(payload.status.value, f"Your application for {application.job.title} is now {payload.status.value}"))
    return application
