from __future__ import annotations

from datetime import datetime
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.learning import LearningSample
from app.models.template import PromptTemplate
from app.models.template_candidate import TemplateCandidate


def _normalize_requirement(text: str) -> str:
    return "".join((text or "").lower().split())


def rebuild_template_candidates(db: Session, min_count: int = 2) -> int:
    # Keep approved candidates, rebuild only pending/rejected pool from latest learning samples.
    db.execute(delete(TemplateCandidate).where(TemplateCandidate.status != "approved"))
    grouped = db.execute(
        select(LearningSample.raw_requirement, func.count(LearningSample.id))
        .where(LearningSample.result_status == "success")
        .group_by(LearningSample.raw_requirement)
        .order_by(func.count(LearningSample.id).desc())
        .limit(200)
    ).all()
    inserted = 0
    seen_normalized: set[str] = set()
    for requirement, count in grouped:
        if count < min_count:
            continue
        normalized = _normalize_requirement(requirement)
        if not normalized or normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        existing_template = db.scalar(
            select(PromptTemplate).where(PromptTemplate.default_requirement == requirement)
        )
        if existing_template:
            continue
        candidate = TemplateCandidate(
            name=f"候选模板-{inserted + 1}",
            category="drop_rate",
            description=f"由学习样本聚合生成，出现 {count} 次",
            default_requirement=requirement,
            source_count=int(count),
            status="pending",
        )
        db.add(candidate)
        inserted += 1
    db.commit()
    return inserted


def approve_template_candidate(db: Session, candidate: TemplateCandidate) -> PromptTemplate:
    template = PromptTemplate(
        name=f"{candidate.name}-approved-{candidate.id}",
        category=candidate.category,
        engine="ALL",
        description=candidate.description,
        default_requirement=candidate.default_requirement,
    )
    db.add(template)
    candidate.status = "approved"
    candidate.approved_at = datetime.utcnow()
    db.add(candidate)
    db.commit()
    db.refresh(template)
    return template


def reject_template_candidate(db: Session, candidate: TemplateCandidate, note: str = "") -> None:
    candidate.status = "rejected"
    candidate.review_note = note
    db.add(candidate)
    db.commit()
