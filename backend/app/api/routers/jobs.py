from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

import asyncio

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import Job, SavedJob, User, UserRole
from app.models.enums import ExperienceLevel, JobType
from app.schemas.jobs import JobCreate, JobRead, JobUpdate
from app.services.notifications import manager
from app.services.skills import get_or_create_skills

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def job_query(db: Session):
    return db.query(Job).options(selectinload(Job.skills), selectinload(Job.company))


@router.get("", response_model=list[JobRead])
def list_jobs(
    q: str | None = None,
    location: str | None = None,
    salary_min: int | None = None,
    skills: str | None = Query(default=None, description="Comma-separated skill names"),
    job_type: JobType | None = None,
    experience_level: ExperienceLevel | None = None,
    db: Session = Depends(get_db),
) -> list[Job]:
    query = job_query(db).filter(Job.is_active.is_(True))
    if q:
        query = query.filter(Job.title.ilike(f"%{q}%") | Job.description.ilike(f"%{q}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if salary_min is not None:
        query = query.filter((Job.salary_max.is_(None)) | (Job.salary_max >= salary_min))
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    if skills:
        skill_names = [skill.strip().lower() for skill in skills.split(",") if skill.strip()]
        for skill_name in skill_names:
            query = query.filter(Job.skills.any(name=skill_name))
    return query.order_by(Job.created_at.desc()).all()


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> Job:
    data = payload.model_dump(exclude={"skills"})
    job = Job(**data, recruiter_id=current_user.id)
    job.skills = get_or_create_skills(db, payload.skills)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/mine", response_model=list[JobRead])
def my_jobs(
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> list[Job]:
    return job_query(db).filter(Job.recruiter_id == current_user.id).order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = job_query(db).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdate,
    current_user: User = Depends(require_roles(UserRole.recruiter, UserRole.admin)),
    db: Session = Depends(get_db),
) -> Job:
    job = job_query(db).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role != UserRole.admin and job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can update only your own jobs")
    data = payload.model_dump(exclude_unset=True, exclude={"skills"})
    for field, value in data.items():
        setattr(job, field, value)
    if payload.skills is not None:
        job.skills = get_or_create_skills(db, payload.skills)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.recruiter, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role != UserRole.admin and job.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can delete only your own jobs")
    db.delete(job)
    db.commit()
    asyncio.create_task(manager.send_to_all({"type": "job_deleted", "job_id": job_id}))


@router.post("/{job_id}/save", status_code=status.HTTP_201_CREATED)
def save_job(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not db.query(Job).filter(Job.id == job_id, Job.is_active.is_(True)).first():
        raise HTTPException(status_code=404, detail="Job not found")
    if not db.query(SavedJob).filter(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id).first():
        db.add(SavedJob(user_id=current_user.id, job_id=job_id))
        db.commit()
    return {"message": "Job saved"}


@router.get("/saved/me", response_model=list[JobRead])
def saved_jobs(
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> list[Job]:
    return (
        job_query(db)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .filter(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
        .all()
    )
