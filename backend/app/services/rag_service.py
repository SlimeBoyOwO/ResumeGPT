import os
import json
import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import chromadb
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.models.match_record import MatchRecord
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('rag_debug.log', encoding='utf-8')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(fh)

# Singletons for memory efficiency across the FastAPI app
try:
    logger.info("正在加载 BERT 向量模型 (m3e-base)...")
    model = SentenceTransformer('moka-ai/m3e-base')
except Exception as e:
    logger.warning(f"Failed to load sentence-transformer: {e}")
    model = None

try:
    logger.info("正在初始化 ChromaDB 向量数据库...")
    os.makedirs(settings.UPLOAD_DIR / "chroma_data", exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(settings.UPLOAD_DIR / "chroma_data"))
    
    resume_col = chroma_client.get_or_create_collection(name="resume_collection", metadata={"hnsw:space": "cosine"})
    jd_col = chroma_client.get_or_create_collection(name="jd_collection", metadata={"hnsw:space": "cosine"})
    logger.info("模型与数据库加载完成！\n")
except Exception as e:
    logger.warning(f"Failed to load ChromaDB: {e}")
    chroma_client = None
    resume_col = None
    jd_col = None

edu_level = {
    "大专": 1, "本科": 2, "学士": 2, 
    "硕士": 3, "研究生": 3, "博士": 4
}

def parse_resume(resume_data: dict[str, Any]):
    name = resume_data.get("姓名") or "未知候选人"
    
    resume_edu = "未知"
    edu_val = 0
    edu_list = resume_data.get("教育经历") or []
    for edu in edu_list:
        degree = (edu.get("学位") or "") + (edu.get("最高学历") or "")
        for k, v in edu_level.items():
            if k in degree and v > edu_val:
                edu_val = v
                resume_edu = degree
    
    semantic_text_parts = []
    work_list = resume_data.get("工作经历") or []
    for work in work_list:
        text = f"【职务】{work.get('职务', '')} 【工作内容】{work.get('工作内容', '')}"
        semantic_text_parts.append(text)
        
    proj_list = resume_data.get("项目经历") or []
    for proj in proj_list:
        text = f"【参与项目】{proj.get('项目名称', '')} 【项目责任】{proj.get('项目责任', '')}"
        semantic_text_parts.append(text)
        
    semantic_text = "\n".join(semantic_text_parts)
    return name, resume_edu, edu_val, semantic_text


async def ingest_resume(resume_id: int):
    """
    Called by background task after a Resume is uploaded and parsed.
    """
    logger.info(f"Starting ingest_resume for ID {resume_id}")
    try:
        if not model or not resume_col:
            if not model:
                logger.error("RAG logic aborted: model is None.")
            if not resume_col:
                logger.error("RAG logic aborted: resume_col is None.")
            return

        async with async_session_factory() as session:
            resume = await session.get(Resume, resume_id)
            if not resume or not resume.ner_extracted_data:
                logger.warning(f"Resume {resume_id} not found or ner_extracted_data is empty.")
                return

            name, resume_edu, edu_val, semantic_text = parse_resume(resume.ner_extracted_data)
            if not semantic_text.strip():
                logger.info(f"Resume {resume_id} dropped from RAG (no semantic text).")
                return
                
            embedding = model.encode(semantic_text).tolist()
            vector_db_id = f"r_{resume.id}"
            
            resume_col.upsert(
                ids=[vector_db_id],
                embeddings=[embedding],
                documents=[semantic_text],
                metadatas=[{"id": resume.id, "name": name, "edu": resume_edu, "edu_val": edu_val}]
            )
            
            resume.vector_id = vector_db_id
            await session.commit()
            logger.info(f"Successfully vectorized Resume {resume_id}.")

            # Match with all JDs
            await _match_resume_to_all_jds(session, resume_id, embedding, edu_val)
    except Exception as e:
        logger.error(f"CRASH in ingest_resume: {e}", exc_info=True)
        
    # Trigger fine screening for affected JDs
    try:
        from app.services.workflow_engine import auto_trigger_fine_screening
        async with async_session_factory() as session:
            jd_ids = await session.execute(select(MatchRecord.jd_id).where(MatchRecord.resume_id == resume_id))
            for jd_id in set(jd_ids.scalars().all()):
                await auto_trigger_fine_screening(jd_id)
    except Exception as e:
        logger.error(f"Trigger failed: {e}", exc_info=True)


async def ingest_job_description(jd_id: int):
    """
    Called by background task when JD is created.
    """
    logger.info(f"Starting ingest_job_description for ID {jd_id}")
    try:
        if not model or not jd_col:
            logger.error("RAG logic aborted: model or jd_col is None.")
            return

        async with async_session_factory() as session:
            jd = await session.get(JobDescription, jd_id)
            if not jd or not jd.description:
                logger.warning(f"JD {jd_id} not found or description is empty.")
                return

            embedding = model.encode(jd.description).tolist()
            vector_db_id = f"jd_{jd.id}"
            
            jd_col.upsert(
                ids=[vector_db_id],
                embeddings=[embedding],
                documents=[jd.description],
                metadatas=[{"id": jd.id, "title": str(jd.title) if jd.title else "未知"}]
            )
            
            jd.vector_id = vector_db_id
            await session.commit()
            logger.info(f"Successfully vectorized JD {jd_id}.")
            
            # Match with all Resumes
            await _match_jd_to_all_resumes(session, jd, embedding)
    except Exception as e:
        logger.error(f"CRASH in ingest_job_description: {e}", exc_info=True)
        
    # Trigger fine screening for this JD
    try:
        from app.services.workflow_engine import auto_trigger_fine_screening
        await auto_trigger_fine_screening(jd_id)
    except Exception as e:
        logger.error(f"Trigger failed: {e}", exc_info=True)


async def _match_resume_to_all_jds(session: AsyncSession, resume_id: int, resume_embedding: list[float], resume_edu_val: int):
    if not jd_col: return
    try:
        results = jd_col.query(
            query_embeddings=[resume_embedding],
            n_results=100,
            include=["metadatas", "distances"]
        )
        
        if not results or not results.get('ids') or not results['ids'][0]:
            return

        ids = results['ids'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]

        for i in range(len(ids)):
            jd_db_id = metadatas[i]["id"]
            semantic_score = max(0, (1 - distances[i])) * 100
            
            jd_obj = await session.get(JobDescription, jd_db_id)
            if not jd_obj: continue

            hard_score = 0
            required_edu_val = 2 # default to bachelor
            
            if resume_edu_val >= required_edu_val:
                hard_score = 100
            elif resume_edu_val > 0:
                hard_score = 60

            total = round(0.3 * hard_score + 0.7 * semantic_score, 2)
            await _upsert_match_record(session, jd_db_id, resume_id, total)
            
        logger.info(f"Successfully matched Resume {resume_id} to {len(ids)} JDs.")
    except Exception as e:
        logger.error(f"CRASH in _match_resume_to_all_jds: {e}", exc_info=True)


async def _match_jd_to_all_resumes(session: AsyncSession, jd: JobDescription, jd_embedding: list[float]):
    if not resume_col: return
    try:
        results = resume_col.query(
            query_embeddings=[jd_embedding],
            n_results=1000, 
            include=["metadatas", "distances"]
        )

        if not results or not results.get('ids') or not results['ids'][0]:
            return

        ids = results['ids'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]

        for i in range(len(ids)):
            resume_db_id = metadatas[i]["id"]
            
            # 避免 ChromaDB 存在残留数据，而在 MySQL 已经被删除导致 Foreign Key 约束报错终止匹配
            resume_obj = await session.get(Resume, resume_db_id)
            if not resume_obj: continue
            
            resume_edu_val = metadatas[i]["edu_val"]
            
            semantic_score = max(0, (1 - distances[i])) * 100
            
            hard_score = 0
            required_edu_val = 2
            if resume_edu_val >= required_edu_val:
                hard_score = 100
            elif resume_edu_val > 0:
                hard_score = 60

            total = round(0.3 * hard_score + 0.7 * semantic_score, 2)
            await _upsert_match_record(session, jd.id, resume_db_id, total)
            
        logger.info(f"Successfully matched JD {jd.id} to {len(ids)} Resumes.")
    except Exception as e:
        logger.error(f"CRASH in _match_jd_to_all_resumes: {e}", exc_info=True)


async def _upsert_match_record(session: AsyncSession, jd_id: int, resume_id: int, total_score: float):
    query = select(MatchRecord).where(MatchRecord.jd_id == jd_id, MatchRecord.resume_id == resume_id)
    result = await session.execute(query)
    record = result.scalars().first()

    if record:
        record.vector_similarity = total_score
        # 不更新 final_score，保留为精筛后的最终评分
        if record.workflow_status == 'failed':
            record.workflow_status = 'rough_matching'
    else:
        new_record = MatchRecord(
            jd_id=jd_id,
            resume_id=resume_id,
            workflow_status="rough_matching",
            vector_similarity=total_score,
            final_score=None
        )
        session.add(new_record)
        
    await session.commit()
