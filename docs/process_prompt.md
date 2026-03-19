## 后端集合 RAG 系统，存储到向量数据库。

现在我们把注意力转移到后端。目前我们已经实现了JD的上传，简历的上传以及对简历的分析。现在我们要实现的功能是：粗筛。

粗筛原理主要通过一下代码实现：

```python
import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

# ==========================================
# 1. 初始化模型与向量数据库 (ChromaDB)
# ==========================================
print("正在加载 BERT 向量模型 (m3e-base)...")
model = SentenceTransformer('moka-ai/m3e-base')

print("正在初始化 ChromaDB 向量数据库...")
# 创建一个存在内存中的 ChromaDB 客户端（如果需要存硬盘，用 PersistentClient）
chroma_client = chromadb.Client()

# 创建集合 (Collection)，指定距离计算方式为 cosine (余弦相似度)
# ChromaDB 默认是 L2 距离，做语义文本匹配一定要改成 cosine
try:
    chroma_client.delete_collection("resume_collection") # 避免重复运行报错
except:
    pass
collection = chroma_client.create_collection(
    name="resume_collection",
    metadata={"hnsw:space": "cosine"}
)
print("模型与数据库加载完成！\n")

# ==========================================
# 2. 核心匹配引擎
# ==========================================
class RAGResumeMatcher:
    def __init__(self, embedding_model, vector_db_collection):
        self.model = embedding_model
        self.collection = vector_db_collection

        # 学历权重字典
        self.edu_level = {
            "大专": 1, "本科": 2, "学士": 2,
            "硕士": 3, "研究生": 3, "博士": 4
        }

    def parse_resume(self, resume_data):
        """解析新的嵌套 JSON 格式，提取硬性指标和软性长文本"""
        # 1. 提取基础信息
        name = resume_data.get("姓名", "未知候选人")

        # 2. 提取最高学历 (遍历教育经历)
        resume_edu = "未知"
        edu_val = 0
        for edu in resume_data.get("教育经历", []):
            degree = edu.get("学位", "") + edu.get("最高学历", "")
            for k, v in self.edu_level.items():
                if k in degree and v > edu_val:
                    edu_val = v
                    resume_edu = degree

        # 3. 拼接用于语义匹配的软性长文本 (工作内容 + 项目责任)
        semantic_text_parts = []
        for work in resume_data.get("工作经历", []):
            text = f"【职务】{work.get('职务', '')} 【工作内容】{work.get('工作内容', '')}"
            semantic_text_parts.append(text)

        for proj in resume_data.get("项目经历", []):
            text = f"【参与项目】{proj.get('项目名称', '')} 【项目责任】{proj.get('项目责任', '')}"
            semantic_text_parts.append(text)

        semantic_text = "\n".join(semantic_text_parts)

        return name, resume_edu, edu_val, semantic_text

    def ingest_to_vectordb(self, resume_id, resume_data):
        """将简历处理后存入 ChromaDB 向量数据库 (RAG的Indexing阶段)"""
        name, resume_edu, edu_val, semantic_text = self.parse_resume(resume_data)

        if not semantic_text.strip():
            print(f"警告：{name} 缺乏工作/项目经验，跳过向量化。")
            return None

        # 将文本转为 768维 向量 (ChromaDB 要求传入 Python List)
        embedding = self.model.encode(semantic_text).tolist()

        # 存入数据库
        self.collection.add(
            ids=[resume_id],
            embeddings=[embedding],
            documents=[semantic_text], # 存入原文本，RAG阶段备用
            metadatas=[{"name": name, "edu": resume_edu, "edu_val": edu_val}] # 存入结构化元数据
        )
        print(f"成功将候选人 [{name}] 的经验特征存入 ChromaDB 向量库。")

    def search_and_score(self, jd_text, required_edu_val=2, alpha=0.3, beta=0.7):
        """用 JD 在向量库中检索并进行双路打分 (RAG的Retrieval阶段)"""
        # 1. 将 JD 转化为查询向量
        jd_embedding = self.model.encode(jd_text).tolist()

        # 2. 从 ChromaDB 中检索最匹配的 1 份简历
        results = self.collection.query(
            query_embeddings=[jd_embedding],
            n_results=1,
            include=["metadatas", "distances", "documents"]
        )

        if not results['ids'][0]:
            return "库中没有简历。"

        # 3. 解析检索结果
        match_id = results['ids'][0][0]
        metadata = results['metadatas'][0][0]
        name = metadata['name']
        resume_edu = metadata['edu']
        resume_edu_val = metadata['edu_val']

        # ChromaDB 返回的 cosine 距离 (Distance)
        # 余弦距离 = 1 - 余弦相似度。所以我们要转换回相似度得分 (0~100)
        distance = results['distances'][0][0]
        semantic_score = max(0, (1 - distance)) * 100

        # 4. 计算硬性规则得分 (学历)
        hard_score = 0
        if resume_edu_val >= required_edu_val:
            hard_score = 100
        elif resume_edu_val > 0:
            hard_score = 60

        # 5. 计算综合得分
        total_score = (alpha * hard_score) + (beta * semantic_score)

        return {
            "name": name,
            "resume_edu": resume_edu,
            "hard_score": hard_score,
            "semantic_score": round(semantic_score, 2),
            "total_score": round(total_score, 2)
        }
```

> 注意：其中双阶段重排部分，这里的排序比较傻，目前先实现仅通过向量搜寻相似度搜寻，并预留双阶段重排的接口。

工作需要包含以下方面：

1. 当 JD 被上传后，需要对 JD 进行向量化，并存入向量数据库。
2. 当简历被上传后，需要对简历进行向量化，并存入向量数据库。
3. 每当一份简历被上传并存入向量数据库中，立马与所有已上传的 JD 进行匹配
4. 同理，每当一个 JD 被上传并存入向量数据库中，立马与所有已上传的简历进行匹配

前端需要注意的地方：

1. 为用户前端额外增加一个查看简历初筛分数最高的 Top 10 匹配的 JD 的页面
2. 为管理员（即上传 JD 的用户）额外增加一个查看 JD 初筛分数最高的 Top N 匹配的简历的页面
3. 为 JD 上传的时候额外增加一个预期岗位的属性，用于确定上一条的 Top N 的 N 的值
4. 初筛结束后，记得更新数据库中状态，并且预留接下来用LLM进行精排的接口（LLM就是上文提到的多专家节点流多路评分功能。）

数据库需要注意的地方：

注意 mysql 中，简历和JD都有向量数据库id的属性，要匹配上向量数据库。

## 后端在`粗筛`之后，根据节点流进行大模型评分和输出

现在我们完成了粗筛选的过程，让我们进行细筛选。

1. 细筛需要粗筛的分数达到85以上才进行，否则自动忽视（即不进行细筛），并且只进行初筛分数前 N 条（N代表JD所需求的岗位数量）
2. 细筛会根据数据库中，JD存储的专家节点流进行对LLM的调用，输出自己的评分和评价。
3. 注意：如果某节点的前面有节点，则他的输入是简历信息+前一个节点输出的信息。
4. 输出的评分和评价会存储到`expert_evaluations`表中
5. 所有节点评价完毕后，根据权重计算最终的得分（满分100），也就是`match_records`表的`final_score`，再额外调用一个LLM，输出六维度的能力图。
6. 管理员前端可以查看某份简历的具体的评分信息，六维度能力图以及最终的分数（从高到低排序N个）
