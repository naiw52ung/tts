from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.template import PromptTemplate

DEFAULT_TEMPLATES = [
    {
        "name": "全服怪物爆率提升20%",
        "category": "drop_rate",
        "engine": "ALL",
        "description": "将 MonItems 全部怪物爆率提升 20%",
        "default_requirement": "将全部怪物爆率提升20%",
    },
    {
        "name": "祖玛系爆率提升30%",
        "category": "drop_rate",
        "engine": "ALL",
        "description": "仅提升祖玛相关怪物爆率",
        "default_requirement": "将祖玛怪物爆率提升30%",
    },
    {
        "name": "赤月系爆率提升15%",
        "category": "drop_rate",
        "engine": "ALL",
        "description": "仅提升赤月相关怪物爆率",
        "default_requirement": "将赤月怪物爆率提升15%",
    },
]


def seed_templates(db: Session) -> None:
    existing = db.scalars(select(PromptTemplate.name)).all()
    existing_set = set(existing)
    for item in DEFAULT_TEMPLATES:
        if item["name"] in existing_set:
            continue
        db.add(PromptTemplate(**item))
    db.commit()
