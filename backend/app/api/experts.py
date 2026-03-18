"""Expert management APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models.expert import Expert
from app.models.user import User
from app.schemas.expert import ExpertOptionResponse

router = APIRouter(prefix="/api/experts", tags=["experts"])


@router.get("/", response_model=list[ExpertOptionResponse])
async def list_experts(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    result = await db.execute(select(Expert).order_by(Expert.created_at.desc()))
    experts = result.scalars().all()
    return [
        ExpertOptionResponse(
            id=e.id, 
            name=e.name, 
            description=e.description, 
            system_prompt=e.system_prompt
        ) for e in experts
    ]
