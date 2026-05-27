import json
import logging

import httpx

from app.core.config import settings
from app.models import Application
from app.services.matching import calculate_match_score

logger = logging.getLogger(__name__)


def _candidate_text(application: Application) -> str:
    profile = application.applicant_profile
    if not profile:
        return ""
    return " ".join(
        value or ""
        for value in [
            profile.headline,
            profile.summary,
            profile.education,
            profile.experience,
            " ".join(skill.name for skill in profile.skills),
            profile.resume_text,
        ]
    )


def _fallback_suitability(application: Application) -> dict:
    profile_text = _candidate_text(application).lower()
    required_skills = [skill.name.lower() for skill in application.job.skills]
    matched_skills = [skill for skill in required_skills if skill in profile_text]
    missing_skills = [skill for skill in required_skills if skill not in matched_skills]
    skill_score = (len(matched_skills) / len(required_skills)) if required_skills else 0
    score_out_of_10 = round(skill_score * 10, 1)
    return {
        "score_out_of_10": score_out_of_10,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "summary": "Generated using local skill matching.",
        "recommendation": "Strong fit" if score_out_of_10 >= 7 else "Needs review" if score_out_of_10 >= 4 else "Low fit",
        "source": "local",
    }


async def check_ai_suitability(application: Application) -> dict:
    fallback = _fallback_suitability(application)
    if not settings.OPENAI_API_KEY:
        return fallback

    profile_text = _candidate_text(application)[:6000]
    required_skills = [skill.name for skill in application.job.skills]
    prompt = {
        "job_title": application.job.title,
        "job_description": application.job.description,
        "required_skills": required_skills,
        "candidate_name": application.applicant.full_name if application.applicant else "Applicant",
        "candidate_resume_and_profile": profile_text,
    }
    system_message = (
        "You are a recruiter assistant. Compare required job skills with candidate resume/profile text. "
        "Return only valid JSON with keys: score_out_of_10, matched_skills, missing_skills, summary, recommendation. "
        "score_out_of_10 must be a number from 0 to 10."
    )

    def _parse_json_content(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end >= start:
                return json.loads(text[start:end + 1])
            raise

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = _parse_json_content(content)
            if not isinstance(result, dict):
                raise ValueError("OpenAI response was not a JSON object")
    except Exception as e:
        logger.warning(f"OpenAI API call failed: {str(e)}. Using local fallback.")
        return fallback

    score = result.get("score_out_of_10", fallback["score_out_of_10"])
    try:
        score = max(0, min(10, round(float(score), 1)))
    except (TypeError, ValueError):
        score = fallback["score_out_of_10"]

    matched_skills = result.get("matched_skills") or fallback["matched_skills"]
    required_count = len(required_skills)
    skill_ratio_score = round((len(matched_skills) / required_count) * 10, 1) if required_count else score
    score = max(score, skill_ratio_score)

    return {
        "score_out_of_10": score,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": result.get("missing_skills") or fallback["missing_skills"],
        "summary": result.get("summary") or fallback["summary"],
        "recommendation": result.get("recommendation") or fallback["recommendation"],
        "source": "openai",
    }
