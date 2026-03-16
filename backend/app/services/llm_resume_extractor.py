"""LLM-based resume extraction."""

from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import settings


SYSTEM_PROMPT = """
你是一个专业的简历解析算法。请从以下文本中提取信息，并严格按照 JSON 格式输出。
必须包含以下字段，如没有找到请填入 null 或空列表：
{
  "姓名": "",
  "电话": "",
  "最高学历": "",
  "教育经历": [{"毕业院校": "", "学位": "", "毕业时间": ""}],
  "工作经历": [{"工作单位": "", "职务": "", "工作时间": ""}],
  "项目经历": [{"项目名称": "", "项目时间": ""}]
}
"""


def _get_client() -> OpenAI:
    if not settings.CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is not configured.")
    return OpenAI(api_key=settings.CHAT_API_KEY, base_url=settings.CHAT_API_BASE_URL)


def parse_resume_with_llm(text: str) -> dict:
    client = _get_client()
    prompt_text = text[:2000]
    response = client.chat.completions.create(
        model=settings.CHAT_API_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"简历文本：\n{prompt_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    result_str = response.choices[0].message.content or "{}"
    return json.loads(result_str)
