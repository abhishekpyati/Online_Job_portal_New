# Online Job Portal

A full-stack jobs marketplace built with FastAPI, MySQL, SQLAlchemy, Alembic, JWT, role-based access control, a Vite frontend, and optional OpenAI-powered suitability scoring.

## Features

- Applicant, recruiter, and admin roles
- JWT login with bcrypt password hashing
- Applicant profiles with skills, resume upload, profile image upload, saved jobs, and application tracking
- Recruiter company profiles, job CRUD, applicant review, status updates, and candidate matching
- OpenAI-enhanced suitability checks with fallback skill match scoring
- Applicant dashboard company search/filter and recruiter application suitability details
- Resume download for recruiters and persistent applicant profile resume storage
- Recruiter company detail update persistence via dedicated API route
- Real-time notifications via FastAPI WebSockets
- Admin analytics, user/job moderation, and platform audit visibility
- Docker Compose support for backend, frontend, and MySQL services

## Project Structure

```text
backend/
  app/
    api/routers/       FastAPI endpoints
    core/              settings and security
    db/                SQLAlchemy engine/session
    models/            ORM models and relationships
    schemas/           Pydantic request/response models
    services/          AI suitability, matching, files, notifications
  alembic/             database migrations
frontend/
  index.html           Bootstrap-based single-page app
  styles.css
  app.js
uploads/
  resumes/
  profile_images/
docker-compose.yml
```



### 1. Start MySQL

Use your own local MySQL instance or start the MySQL container:

```bash
docker-compose up -d mysql
```

If you use the MySQL container, the local database URL is:



### 2. Start the Backend

```bash
cd backend
python -m pip install -r requirements.txt
```

Set environment variables (PowerShell example):



Run migrations:

```bash
python -m alembic upgrade head
```

Start the server:

```bash
python -m uvicorn main:app --port 8000 --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Docker Compose

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:8090`
- Backend docs: `http://localhost:8000/docs`

## Authentication and Role APIs

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`

## Profile APIs

- `GET /api/profiles/applicant/me`
- `PUT /api/profiles/applicant/me`
- `POST /api/profiles/applicant/resume`
- `POST /api/profiles/applicant/image`
- `GET /api/profiles/company/me`
- `POST /api/profiles/company/me`
- `PUT /api/profiles/company/me`

## Job APIs

- `GET /api/jobs`
- `GET /api/jobs/mine`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs`
- `PUT /api/jobs/{job_id}`
- `DELETE /api/jobs/{job_id}`

## Application APIs

- `POST /api/applications`
- `GET /api/applications/me`
- `GET /api/applications/recruiter`
- `PUT /api/applications/{application_id}/status`

## Matching and Notifications

- `GET /api/matching/recommended-jobs`
- `GET /api/matching/jobs/{job_id}/candidates`
- `GET /api/notifications`
- `WS /api/notifications/ws?token=...`
- `GET /api/admin/analytics`

## Notes

- The login UI no longer exposes admin credentials by default.
- Store real secrets in `.env` for development and production.
- Protect uploaded files in production, and use HTTPS with a reverse proxy.
- Add automated tests and CI before deploying to production.
