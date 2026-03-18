"""Job description management APIs."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_admin
from app.models.expert import Expert
from app.models.job_description import JobDescription
from app.models.user import User
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionListResponse,
    JobDescriptionResponse,
)

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
        created_at=item.created_at,
        workflow_mode="manual" if item.workflow_graph else "auto_pending",
        workflow_graph=item.workflow_graph,
    )


@router.post("/", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    body: JobDescriptionCreate,
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
        workflow_graph=body.workflow_graph if not body.auto_select_experts else None,
    )
    db.add(jd)
    await db.flush()

    # Re-fetch the saved object to refresh fields from db
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd.id))
    created = result.scalar_one()
    return _to_response(created)


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
