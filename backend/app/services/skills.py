from sqlalchemy.orm import Session

from app.models import Skill


def get_or_create_skills(db: Session, names: list[str]) -> list[Skill]:
    skills: list[Skill] = []
    cleaned_names = sorted({name.strip().lower() for name in names if name and name.strip()})
    for name in cleaned_names:
        skill = db.query(Skill).filter(Skill.name == name).first()
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
            db.flush()
        skills.append(skill)
    return skills
