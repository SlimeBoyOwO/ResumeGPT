"""简历管理路由"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.resume import Resume
from app.models.user import User
from app.models.match_record import MatchRecord
from app.models.job_description import JobDescription
from app.services.rag_service import ingest_resume
from app.schemas.common import MessageResponse
from app.schemas.resume import ResumeResponse, ResumeListResponse
from app.services.resume_extraction import ExtractionError, extract_resume_data

router = APIRouter(prefix="/api/resumes", tags=["简历"])


def _validate_file(file: UploadFile) -> str:
    """验证上传文件类型和大小"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_RESUME_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_RESUME_EXTENSIONS)
        raise HTTPException(status_code=400, detail=f"不支持的文件格式。允许的格式：{allowed}")

    return ext


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    bg_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="简历文件 (PDF/DOCX/图片)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户上传简历"""
    ext = _validate_file(file)

    # 读取文件内容并检查大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = settings.RESUME_UPLOAD_DIR / unique_filename

    # 保存文件
    file_path.write_bytes(content)

    # 保存到数据库
    resume = Resume(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename or "unknown",
        file_path=str(file_path),
        file_type=ext.lstrip("."),
        status="parsing",
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)

    try:
        extracted_data, _source = await run_in_threadpool(extract_resume_data, str(file_path))
        resume.ner_extracted_data = extracted_data
        resume.status = "parsed"
    except ExtractionError as exc:
        resume.status = "failed"
        if exc.partial_data:
            resume.ner_extracted_data = exc.partial_data
    except Exception:
        resume.status = "failed"
    await db.commit()
    await db.refresh(resume)

    if resume.status == "parsed":
        bg_tasks.add_task(ingest_resume, resume.id)

    return ResumeResponse(
        **{k: v for k, v in resume.__dict__.items() if not k.startswith("_")},
        username=current_user.username,
    )


@router.get("/", response_model=ResumeListResponse)
async def list_my_resumes(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户：获取自己的简历列表"""
    offset = (page - 1) * page_size
    query = select(Resume).where(Resume.user_id == current_user.id)

    if status_filter:
        query = query.where(Resume.status == status_filter)

    # 总数
    count_q = select(func.count(Resume.id)).where(Resume.user_id == current_user.id)
    if status_filter:
        count_q = count_q.where(Resume.status == status_filter)
    total = (await db.execute(count_q)).scalar() or 0

    # 分页
    result = await db.execute(query.order_by(Resume.uploaded_at.desc()).offset(offset).limit(page_size))
    resumes = result.scalars().all()

    return ResumeListResponse(
        total=total,
        items=[
            ResumeResponse(
                **{k: v for k, v in r.__dict__.items() if not k.startswith("_")},
                username=current_user.username,
            )
            for r in resumes
        ],
    )


@router.get("/my-matches")
async def get_my_matches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """求职者：获取所有名下简历的初筛 Top JDs"""
    matches_res = await db.execute(
        select(MatchRecord, JobDescription)
        .join(Resume, MatchRecord.resume_id == Resume.id)
        .join(JobDescription, MatchRecord.jd_id == JobDescription.id)
        .where(Resume.user_id == current_user.id)
        .order_by(MatchRecord.final_score.desc())
        .limit(20)
    )
    rows = matches_res.all()
    results = []
    for match, jd in rows:
        results.append({
            "match_id": match.id,
            "resume_id": match.resume_id,
            "jd_id": jd.id,
            "jd_title": jd.title,
            "jd_department": jd.department,
            "workflow_status": match.workflow_status,
            "vector_similarity": match.vector_similarity,
            "final_score": match.final_score,
        })
    return {"items": results}


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个简历详情"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 普通用户只能查看自己的简历
    if current_user.role != "admin" and resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此简历")

    # 获取关联的用户名
    user_result = await db.execute(select(User.username).where(User.id == resume.user_id))
    username = user_result.scalar_one_or_none()

    return ResumeResponse(
        **{k: v for k, v in resume.__dict__.items() if not k.startswith("_")},
        username=username,
    )


@router.delete("/{resume_id}", response_model=MessageResponse)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除简历"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 普通用户只能删除自己的简历
    if current_user.role != "admin" and resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除此简历")

    # 删除文件
    file_path = Path(resume.file_path)
    if file_path.exists():
        file_path.unlink()

    await db.delete(resume)
    return MessageResponse(message="简历已删除")


# ---- 管理员路由 ----

@router.get("/admin/all", response_model=ResumeListResponse)
async def admin_list_all_resumes(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    username_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：获取所有用户的简历列表"""
    offset = (page - 1) * page_size
    query = select(Resume, User.username).join(User, Resume.user_id == User.id)
    count_query = select(func.count(Resume.id))

    if status_filter:
        query = query.where(Resume.status == status_filter)
        count_query = count_query.where(Resume.status == status_filter)

    if username_filter:
        query = query.join(User, Resume.user_id == User.id, isouter=True).where(
            User.username.ilike(f"%{username_filter}%")
        )
        count_query = count_query.join(User, Resume.user_id == User.id).where(
            User.username.ilike(f"%{username_filter}%")
        )

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        query.order_by(Resume.uploaded_at.desc()).offset(offset).limit(page_size)
    )
    rows = result.all()

    return ResumeListResponse(
        total=total,
        items=[
            ResumeResponse(
                **{k: v for k, v in resume.__dict__.items() if not k.startswith("_")},
                username=username,
            )
            for resume, username in rows
        ],
    )
