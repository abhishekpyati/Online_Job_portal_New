from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Application, Job, User, UserRole
from app.schemas.jobs import JobRead
from app.schemas.users import UserRead

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(_: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, _: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()


@router.get("/jobs", response_model=list[JobRead])
def list_all_jobs(_: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)) -> list[Job]:
    return db.query(Job).options(selectinload(Job.skills), selectinload(Job.company)).order_by(Job.created_at.desc()).all()


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inappropriate_job(job_id: int, _: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


@router.get("/analytics")
def analytics(_: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)) -> dict[str, int]:
    return {
        "users": db.query(User).count(),
        "recruiters": db.query(User).filter(User.role == UserRole.recruiter).count(),
        "applicants": db.query(User).filter(User.role == UserRole.applicant).count(),
        "jobs": db.query(Job).count(),
        "applications": db.query(Application).count(),
    }
