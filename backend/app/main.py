from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, applications, auth, jobs, matching, notifications, profiles, users
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import User, UserRole

app = FastAPI(title="Online Job Portal API", version="1.0.0")

cors_origins = settings.cors_origin_list
if "null" not in cors_origins:
    cors_origins.append("null")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.on_event("startup")
def create_first_admin() -> None:
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
        if not exists:
            db.add(
                User(
                    email=settings.FIRST_ADMIN_EMAIL,
                    full_name="Platform Admin",
                    hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                    role=UserRole.admin,
                )
            )
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
