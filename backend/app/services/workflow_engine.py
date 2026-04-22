"""Workflow engine for Fine Screening using LLM DAGs."""

import json
import logging
from collections import defaultdict, deque
import asyncio

from openai import AsyncOpenAI
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.job_description import JobDescription
from app.models.match_record import MatchRecord
from app.models.resume import Resume
from app.models.expert import Expert
from app.models.expert_evaluation import ExpertEvaluation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _get_async_client() -> AsyncOpenAI:
    if not settings.CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is not configured.")
    return AsyncOpenAI(api_key=settings.CHAT_API_KEY, base_url=settings.CHAT_API_BASE_URL)

async def auto_trigger_fine_screening(jd_id: int):
    """
    Called after rough matching to process the top N resumes that scored >= 85.
    """
    try:
        async with async_session_factory() as session:
            jd = await session.get(JobDescription, jd_id)
            if not jd or not jd.workflow_graph:
                return
            
            top_n = jd.expected_hires
            # Fetch top N resumes >= 80
            query = (
                select(MatchRecord)
                .where(MatchRecord.jd_id == jd_id, MatchRecord.vector_similarity >= 80)
                .order_by(MatchRecord.vector_similarity.desc())
                .limit(top_n)
            )
            result = await session.execute(query)
            top_matches = result.scalars().all()

            for match in top_matches:
                if match.workflow_status == "rough_matching":
                    match.workflow_status = "agent_evaluating"
                    session.add(match)
            await session.commit()
            
            # Start jobs for the ones we just marked as executing
            for match in top_matches:
                if match.workflow_status == "agent_evaluating":
                    asyncio.create_task(run_workflow_for_match(match.id))
    except Exception as e:
        logger.error(f"Failed to trigger fine screening for JD {jd_id}: {e}", exc_info=True)


async def run_workflow_for_match(match_id: int):
    """Executes the complete DAG for a single MatchRecord."""
    logger.info(f"Starting Fine Screening DAG for MatchRecord {match_id}")
    try:
        async with async_session_factory() as session:
            match = await session.get(MatchRecord, match_id)
            if not match:
                return
            jd = await session.get(JobDescription, match.jd_id)
            resume = await session.get(Resume, match.resume_id)
            if not jd or not resume or not jd.workflow_graph:
                match.workflow_status = "failed"
                await session.commit()
                return

            graph = jd.workflow_graph
            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])

            if not nodes:
                # No workflow defined, just default to rough score
                match.final_score = match.vector_similarity
                match.workflow_status = "completed"
                await session.commit()
                return

            # 1. Build Adjacency List and In-degrees
            node_map = {n['id']: n for n in nodes}
            adj = defaultdict(list)
            in_degree = {n['id']: 0 for n in nodes}
            
            for e in edges:
                u, v = e['source'], e['target']
                if u in node_map and v in node_map:
                    adj[u].append(v)
                    in_degree[v] += 1
            
            # Pre-extract plain data to avoid lazy-load issues across sessions
            jd_description = jd.description
            resume_ner_data = resume.ner_extracted_data

            # 2. Execute Topologically
            queue = deque([n_id for n_id, deg in in_degree.items() if deg == 0])
            node_outputs = {} # {id: (score, evaluation_text)}

            while queue:
                batch_nodes = list(queue)
                queue.clear()

                tasks = [
                    _execute_expert_node(match_id, jd_description, resume_ner_data, node_map[n_id], adj, node_outputs)
                    for n_id in batch_nodes
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, n_id in enumerate(batch_nodes):
                    res = batch_results[i]
                    if isinstance(res, Exception):
                        logger.error(f"Node {n_id} crashed: {res}")
                        node_outputs[n_id] = (0, f"Error: {res}")
                    else:
                        node_outputs[n_id] = res

                    for child in adj[n_id]:
                        in_degree[child] -= 1
                        if in_degree[child] == 0:
                            queue.append(child)

            # 3. Calculate Final Score & Weights
            total_weight = 0.0
            weighted_score_sum = 0.0

            for n_id, n_data in node_map.items():
                weight = float(n_data.get('data', {}).get('weight', 1.0))
                score, _ = node_outputs.get(n_id, (0, ""))
                weighted_score_sum += score * weight
                total_weight += weight

            final_score = round(weighted_score_sum / total_weight, 2) if total_weight > 0 else 0.0

            # 4. Generate Radar Chart
            radar_json = await _generate_radar_chart(jd_description, resume_ner_data, node_outputs, node_map)

            # 5. Update Match Record
            match.final_score = final_score
            match.ability_summary = radar_json
            match.workflow_status = "completed"
            await session.commit()
            logger.info(f"Finished DAG for MatchRecord {match_id}. Score: {final_score}")

    except Exception as e:
        logger.error(f"CRASH in run_workflow_for_match {match_id}: {e}", exc_info=True)
        async with async_session_factory() as session:
            match = await session.get(MatchRecord, match_id)
            if match:
                match.workflow_status = "failed"
                await session.commit()


async def _execute_expert_node(match_id: int, jd_description: str, resume_ner_data: dict | None, node: dict, adj: dict, node_outputs: dict) -> tuple[float, str]:
    expert_id = node.get("data", {}).get("expert_id", 0)
    system_prompt = "你是一个资深面试官，请打分评价。"
    if expert_id:
        async with async_session_factory() as db:
            expert = await db.get(Expert, expert_id)
            if expert:
                system_prompt = expert.system_prompt
    node_name = node.get("label", "专家")

    # Reconstruct Context
    base_info = "简历信息:\n"

    # Handle PII Desensitization
    orig_name = resume_ner_data.get("姓名") if resume_ner_data else None
    orig_phone = resume_ner_data.get("电话") if resume_ner_data else None

    def mask_pii(text: str) -> str:
        masked = text
        if orig_name:
            masked = masked.replace(orig_name, "张三")
        if orig_phone:
            masked = masked.replace(orig_phone, "10086114514")
        return masked

    def unmask_pii(text: str) -> str:
        unmasked = text
        if orig_name:
            unmasked = unmasked.replace("张三", orig_name)
        if orig_phone:
            unmasked = unmasked.replace("10086114514", orig_phone)
        return unmasked

    resume_data_str = json.dumps(resume_ner_data, ensure_ascii=False) if resume_ner_data else "无"
    base_info += mask_pii(resume_data_str)

    previous_evals = []
    for p_id, (p_score, p_eval) in node_outputs.items():
         previous_evals.append(f"【前面的专家点评】{p_score}分: {p_eval}")

    if previous_evals:
        base_info += "\n\n其它前置考核评价：\n" + mask_pii("\n".join(previous_evals))

    llm_prompt = f"岗位要求：\n{jd_description}\n\n候选人资料：\n{base_info}\n\n请按照系统提示要求进行评价，结果必须为JSON格式，包含 'score'(0-100的纯数字) 和 'evaluation'(你的详细文字点评)。"

    client = _get_async_client()
    try:
        response = await client.chat.completions.create(
            model=settings.CHAT_API_MODEL,
            messages=[
                {"role": "system", "content": system_prompt + "\n务必使用 JSON 输出，格式： {'score': number, 'evaluation': 'string'}"},
                {"role": "user", "content": llm_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        res_text = response.choices[0].message.content or "{}"
        res_json = json.loads(res_text)
        score = float(res_json.get("score", 0))
        evaluation = str(res_json.get("evaluation", res_text))
        evaluation = unmask_pii(evaluation)
    except Exception as e:
        logger.error(f"Node {node['id']} LLM failure: {e}")
        score = 0.0
        evaluation = f"LLM调用失败或返回格式解析出错。原因: {e}"

    # Save to DB with its own session
    async with async_session_factory() as db:
        query = select(ExpertEvaluation).where(
            ExpertEvaluation.match_record_id == match_id,
            ExpertEvaluation.node_id == node["id"]
        )
        result = await db.execute(query)
        existing_record = result.scalar_one_or_none()

        if existing_record:
            existing_record.expert_id = expert_id
            existing_record.agent_status = "success"
            existing_record.score = score
            existing_record.analysis_content = evaluation
        else:
            evaluation_record = ExpertEvaluation(
                match_record_id=match_id,
                node_id=node["id"],
                expert_id=expert_id,
                agent_status="success",
                score=score,
                analysis_content=evaluation
            )
            db.add(evaluation_record)

        await db.commit()

    return score, evaluation


async def _generate_radar_chart(jd_description: str, resume_ner_data: dict | None, node_outputs: dict, node_map: dict) -> dict:
    """Generate 6-dimension JSON radar data."""
    client = _get_async_client()

    summary_context = f"岗位描述：\n{jd_description}\n\n"

    # Handle PII Desensitization
    orig_name = resume_ner_data.get("姓名") if resume_ner_data else None
    orig_phone = resume_ner_data.get("电话") if resume_ner_data else None

    def mask_pii(text: str) -> str:
        masked = text
        if orig_name:
            masked = masked.replace(orig_name, "张三")
        if orig_phone:
            masked = masked.replace(orig_phone, "10086114514")
        return masked

    resume_data_str = json.dumps(resume_ner_data, ensure_ascii=False) if resume_ner_data else "无"
    summary_context += f"简历信息：\n{mask_pii(resume_data_str)}\n\n"
    
    eval_text_sum = ""
    for n_id, (score, eval_text) in node_outputs.items():
        eval_text_sum += f"[{node_map[n_id]['label']}] 得分:{score}, 点评:{eval_text}\n"
    
    summary_context += "各专家模块评分与点评汇总：\n" + mask_pii(eval_text_sum)

    system_msg = """
你是一个人力资源专家。请综合上方所有资料和评价，对候选人生成一个 6 维度的雷达能力图数据，并以JSON格式严格输出。
六个维度分别为："专业技能", "业务经验", "学习与潜力", "沟通与协作", "抗压与稳定性", "岗位匹配度"。每个维度分数为 0 到 100的整数。
输出格式严格如：
{
  "专业技能": 85,
  "业务经验": 90,
  "学习与潜力": 88,
  "沟通与协作": 92,
  "抗压与稳定性": 80,
  "岗位匹配度": 89
}
"""
    try:
        response = await client.chat.completions.create(
            model=settings.CHAT_API_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": summary_context},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        res_text = response.choices[0].message.content or "{}"
        return json.loads(res_text)
    except Exception as e:
        logger.error(f"Radar chart LLM failure: {e}")
        return {"专业技能": 0, "业务经验": 0, "学习与潜力": 0, "沟通与协作": 0, "抗压与稳定性": 0, "岗位匹配度": 0}
