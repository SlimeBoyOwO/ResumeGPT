"""LLM-based resume extraction."""

from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import settings

# 修改后的 Prompt：增加自我介绍、其他信息字段，并说明有辅助信息
SYSTEM_PROMPT = """
你是一个专业的简历解析算法。请结合提供的【简历原文】和【NER辅助提取结果】，从中提取信息并严格按照 JSON 格式输出。
如果信息没有找到请填入 null 或空列表。
额外说明：关于“最高学历”部分，结合【NER辅助提取结果】中的“学历”字段，如果学历字段为空，则在教育经历中通过学校判断最高学历（职高、大专、本科、硕士、博士等），实在没有填写无。


必须包含以下结构：
{
  "姓名": "",
  "电话": "",
  "性别": "",
  "出生年月": "",
  "最高学历": "",
  "籍贯": "",
  "政治面貌": "",
  "自我介绍": "请提取简历中大段的个人总结、自我评价等内容",
  "其他信息": "如获奖情况、专业技能、证书、语言能力等无法归入上述分类的补充信息",
  "教育经历": [{"毕业院校": "", "学位": "", "毕业时间": ""}],
  "工作经历": [{"工作单位": "", "职务": "", "工作内容": "", "工作时间": ""}],
  "项目经历": [{"项目名称": "", "项目责任": "", "项目时间": ""}]
}
"""

def _get_client() -> OpenAI:
    if not settings.CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is not configured.")
    return OpenAI(api_key=settings.CHAT_API_KEY, base_url=settings.CHAT_API_BASE_URL)

# 增加 ner_hint 参数，将其作为 prompt 的一部分
def parse_resume_with_llm(text: str, ner_hint: dict|None = None) -> dict:
    client = _get_client()
    # 考虑到可能增加了信息，把截断长度略微调大到 3000
    prompt_text = text[:3000] 
    
    # 构造包含原文和 NER 提示的 User Content
    user_content = f"【简历原文】：\n{prompt_text}\n"
    if ner_hint:
        user_content += f"\n【NER辅助提取结果（供参考）】：\n{json.dumps(ner_hint, ensure_ascii=False)}"

    response = client.chat.completions.create(
        model=settings.CHAT_API_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    result_str = response.choices[0].message.content or "{}"
    return json.loads(result_str)