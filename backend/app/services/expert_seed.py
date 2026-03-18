"""Seed default experts for admin JD workflow."""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.expert import Expert

DEFAULT_EXPERTS = [
    {
        "name": "技术能力专家",
        "description": "评估候选人的技术深度、技术栈匹配度与工程能力，输出0-100分。",
        "system_prompt": "你是技术能力评估专家。请基于岗位JD与简历内容，从技术深度、技术栈匹配、工程实践三方面评分并给出理由，满分100分。",
    },
    {
        "name": "项目经验专家",
        "description": "评估项目复杂度、个人贡献和结果导向，输出0-100分。",
        "system_prompt": "你是项目经验评估专家。请从项目复杂度、角色贡献、项目结果与量化产出三方面评分并说明依据，满分100分。",
    },
    {
        "name": "业务匹配专家",
        "description": "评估行业背景与岗位需求匹配度，输出0-100分。",
        "system_prompt": "你是业务匹配评估专家。请从行业经验、业务理解与岗位关键要求匹配度进行评分并解释，满分100分。",
    },
    {
        "name": "HR综合评估专家",
        "description": "评估表达协作、稳定性与综合录用建议，输出0-100分。",
        "system_prompt": "你是HR综合评估专家。请从沟通表达、协作潜力、稳定性与风险点进行评分并给出建议，满分100分。",
    },
]


async def seed_default_experts() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Expert.name))
        existing_names = set(result.scalars().all())

        created = False
        for expert_data in DEFAULT_EXPERTS:
            if expert_data["name"] in existing_names:
                continue
            session.add(Expert(**expert_data))
            created = True

        if created:
            await session.commit()
