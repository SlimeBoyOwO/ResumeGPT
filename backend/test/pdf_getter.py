import pdfplumber
import json
import os
from dotenv import load_dotenv

from openai import OpenAI

# 这里以 DeepSeek 为例 (你也可以换成免费的 GLM-4-Flash)
# 注册即送额度，极度便宜

load_dotenv()

API_KEY = os.environ.get("CHAT_API_KEY", "")
BASE_URL = "https://api.deepseek.com"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t: text += t + "\n"
    return text[:2000] # LLM 也有窗口限制，截取前 2000 字基本够用

def parse_resume_with_llm(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    
    # 核心：系统提示词定义 JSON Schema
    system_prompt = """
    你是一个专业的简历解析算法。请从以下文本中提取信息，并严格按照 JSON 格式输出。
    必须包含以下字段，如果没有找到请填入 null 或空列表：
    {
      "姓名": "",
      "电话": "",
      "最高学历": "",
      "教育经历": [{"毕业院校": "", "学位": "", "毕业时间": ""}],
      "工作经历": [{"工作单位": "", "职务": "", "工作时间": ""}],
      "项目经历": [{"项目名称": "", "项目时间": ""}]
    }
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat", # 或 glm-4-flash
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"简历文本：\n{text}"}
        ],
        response_format={"type": "json_object"}, # 强制输出 JSON
        temperature=0.1
    )
    
    result_str = response.choices[0].message.content
    return json.loads(result_str)

if __name__ == "__main__":
    # 测试运行
    res = parse_resume_with_llm("test/test.pdf")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    pass