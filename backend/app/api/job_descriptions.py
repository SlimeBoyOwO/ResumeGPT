"""Job description management APIs."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_admin
from app.models.expert import Expert
from app.models.job_description import JobDescription
from app.models.match_record import MatchRecord
from app.models.resume import Resume
from app.models.user import User
from app.services.rag_service import ingest_job_description
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionListResponse,
    JobDescriptionResponse,
)
from app.models.expert_evaluation import ExpertEvaluation
from app.models.expert import Expert

router = APIRouter(prefix="/api/job-descriptions", tags=["job-descriptions"])


def _to_response(item: JobDescription) -> JobDescriptionResponse:
    return JobDescriptionResponse(
        id=item.id,
        enterprise_id=item.enterprise_id,
        title=item.title,
        department=item.department,
        description=item.description,
        vector_id=item.vector_id,
        status=item.status,
        expected_hires=item.expected_hires,
        created_at=item.created_at,
        workflow_mode="manual" if item.workflow_graph else "auto_pending",
        workflow_graph=item.workflow_graph,
    )


@router.post("/", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    body: JobDescriptionCreate,
    bg_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    if not body.auto_select_experts and body.workflow_graph:
        expert_ids = [
            node.get("expert_id")
            for node in body.workflow_graph.get("nodes", [])
            if node.get("expert_id")
        ]
        if expert_ids:
            existing = await db.execute(select(Expert.id).where(Expert.id.in_(expert_ids)))
            existing_ids = set(existing.scalars().all())
            missing_ids = sorted(set(expert_ids) - existing_ids)
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"expert ids not found: {missing_ids}",
                )

    jd = JobDescription(
        enterprise_id=admin_user.id,
        title=body.title,
        department=body.department,
        description=body.description,
        status=body.status,
        expected_hires=body.expected_hires,
        workflow_graph=body.workflow_graph if not body.auto_select_experts else None,
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    
    bg_tasks.add_task(ingest_job_description, jd.id)
    return _to_response(jd)

@router.get("/{id}/matches")
async def get_job_matches(
    id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    jd_res = await db.execute(select(JobDescription).where(JobDescription.id == id, JobDescription.enterprise_id == admin_user.id))
    jd = jd_res.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found or no access.")

    # Get top expected_hires match records
    matches_res = await db.execute(
        select(MatchRecord, Resume)
        .join(Resume, MatchRecord.resume_id == Resume.id)
        .where(MatchRecord.jd_id == id)
        .order_by(MatchRecord.final_score.desc())
        .limit(jd.expected_hires)
    )
    rows = matches_res.all()
    
    results = []
    for match, resume in rows:
        results.append({
            "match_id": match.id,
            "workflow_status": match.workflow_status,
            "vector_similarity": match.vector_similarity,
            "final_score": match.final_score,
            "ability_summary": match.ability_summary,
            "resume_id": resume.id,
            "resume_name": resume.ner_extracted_data.get("姓名", "未知") if resume.ner_extracted_data else "未知",
            "resume_filename": resume.original_filename
        })
    return {"items": results}

@router.get("/matches/{match_id}/evaluations")
async def get_match_evaluations(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """获取某次匹配的所有专家评价记录"""
    query = (
        select(ExpertEvaluation, Expert.name)
        .join(Expert, ExpertEvaluation.expert_id == Expert.id)
        .where(ExpertEvaluation.match_record_id == match_id)
    )
    result = await db.execute(query)
    rows = result.all()
    
    evals = []
    for ev, expert_name in rows:
        evals.append({
            "id": ev.id,
            "node_id": ev.node_id,
            "expert_name": expert_name,
            "status": ev.agent_status,
            "score": ev.score,
            "analysis_content": ev.analysis_content,
            "created_at": ev.created_at
        })
    return {"items": evals}


@router.get("/", response_model=JobDescriptionListResponse)
async def list_my_job_descriptions(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    offset = (page - 1) * page_size

    total_q = await db.execute(
        select(func.count(JobDescription.id)).where(JobDescription.enterprise_id == admin_user.id)
    )
    total = total_q.scalar() or 0

    rows = await db.execute(
        select(JobDescription)
        .where(JobDescription.enterprise_id == admin_user.id)
        .order_by(JobDescription.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = rows.scalars().all()

    return JobDescriptionListResponse(
        total=total,
        items=[_to_response(item) for item in items],
    )
