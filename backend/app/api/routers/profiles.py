from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import ApplicantProfile, Company, User, UserRole
from app.schemas.profiles import ApplicantProfileRead, ApplicantProfileUpsert, CompanyBase, CompanyRead
from app.services.files import extract_resume_text, save_upload
from app.services.skills import get_or_create_skills

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("/applicant/me", response_model=ApplicantProfileRead)
def get_applicant_profile(
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> ApplicantProfile:
    profile = (
        db.query(ApplicantProfile)
        .options(selectinload(ApplicantProfile.skills))
        .filter(ApplicantProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        profile = ApplicantProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/applicant/me", response_model=ApplicantProfileRead)
def upsert_applicant_profile(
    payload: ApplicantProfileUpsert,
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> ApplicantProfile:
    profile = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == current_user.id).first()
    if not profile:
        profile = ApplicantProfile(user_id=current_user.id)
        db.add(profile)
    for field in ["phone", "location", "headline", "summary", "education", "experience"]:
        setattr(profile, field, getattr(payload, field))
    profile.skills = get_or_create_skills(db, payload.skills)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/applicant/resume", response_model=ApplicantProfileRead)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> ApplicantProfile:
    profile = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == current_user.id).first()
    if not profile:
        profile = ApplicantProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()
    try:
        path = save_upload(file, "resumes", {".pdf", ".docx"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile.resume_path = path
    profile.resume_text = extract_resume_text(path)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/applicant/image", response_model=ApplicantProfileRead)
def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.applicant)),
    db: Session = Depends(get_db),
) -> ApplicantProfile:
    profile = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == current_user.id).first()
    if not profile:
        profile = ApplicantProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()
    try:
        profile.profile_image_path = save_upload(file, "profile_images", {".jpg", ".jpeg", ".png", ".webp"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/company/me", response_model=list[CompanyRead])
def list_my_companies(
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> list[Company]:
    return db.query(Company).filter(Company.recruiter_id == current_user.id).all()


@router.post("/company/me", response_model=CompanyRead)
def create_company(
    payload: CompanyBase,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> Company:
    company = db.query(Company).filter(Company.recruiter_id == current_user.id).first()
    if company is None:
        company = Company(recruiter_id=current_user.id, **payload.model_dump())
        db.add(company)
    else:
        for field in ["name", "website", "location", "description"]:
            setattr(company, field, getattr(payload, field))
    db.commit()
    db.refresh(company)
    return company


@router.put("/company/me", response_model=CompanyRead)
def update_company(
    payload: CompanyBase,
    current_user: User = Depends(require_roles(UserRole.recruiter)),
    db: Session = Depends(get_db),
) -> Company:
    company = db.query(Company).filter(Company.recruiter_id == current_user.id).first()
    if company is None:
        company = Company(recruiter_id=current_user.id, **payload.model_dump())
        db.add(company)
    else:
        for field in ["name", "website", "location", "description"]:
            setattr(company, field, getattr(payload, field))
    db.commit()
    db.refresh(company)
    return company
