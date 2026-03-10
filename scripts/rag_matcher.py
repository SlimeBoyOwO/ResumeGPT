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

# ==========================================
# 3. 运行测试
# ==========================================
if __name__ == "__main__":
    # 你提供的嵌套 JSON 数据
    mock_resume_json = {
        "项目经历": [
            {
            "项目名称": "理论研究",
            "项目时间": "2008.10-2010.07"
            },
            {
            "项目名称": "习近平总书记治国理政现代化战略思想比较研究",
            "项目时间": "2005年02月-2010年10月"
            },
            {
            "项目名称": "信息技术革命与当代认识论研究",
            "项目时间": "2003.12-2018.04"
            },
            {
            "项目名称": "统战部——统战理论研究",
            "项目时间": "2008/05-2019/10"
            }
        ],
        "教育经历": [
            {
            "毕业院校": "北京卫生职业学院",
            "学位": "博士学位",
            "毕业时间": "2017.02"
            },
            {
            "毕业院校": "北京开放大学",
            "学位": "硕士学位",
            "毕业时间": "2011.04"
            }
        ],
        "工作经历": [
            {
            "工作单位": "中国太平洋保险股份有限公司",
            "职务": "翻译实习生",
            "工作时间": "1992/03-2011/05"
            }
        ],
        "姓名": "皮茗婵",
        "电话": "15604126069",
        "最高学历": "硕士研究生"
        }

    # 模拟一份 JD
    mock_jd_text = """
    【岗位名称】理论研究员/翻译
    【岗位职责】
    1. 负责国内外相关政策、现代化治理理论的文献翻译与研究工作。
    2. 参与重点研究课题（如国家治理思想比较研究等），撰写研究报告。
    3. 负责保险或金融相关文件的部分外文处理。
    【任职要求】
    1. 要求本科及以上学历，翻译、政治学、经济学相关专业优先。
    2. 具备优秀的文字表达能力和英文翻译能力。
    3. 拥有理论研究或政府政策研究项目经验者优先考虑。
    """

    # 实例化引擎
    matcher = RAGResumeMatcher(model, collection)
    
    # 步骤 1：入库 (Ingestion) - 将简历写入 ChromaDB
    print("\n>>> 阶段 1: 简历入库 (Vector Database Ingestion)")
    matcher.ingest_to_vectordb(resume_id="resume_001", resume_data=mock_resume_json)
    
    # 步骤 2：检索与打分 (Retrieval & Scoring)
    print("\n>>> 阶段 2: RAG 语义检索与双路打分")
    # JD要求本科(edu_val=2)
    result = matcher.search_and_score(mock_jd_text, required_edu_val=2, alpha=0.3, beta=0.7)
    
    print("\n" + "="*40)
    print(f"匹配候选人: {result['name']}")
    print("-" * 30)
    print(f"📌 [第一路] 结构化规则得分 (权重30%): {result['hard_score']}/100")
    print(f"   说明: 简历提取出学历为 '{result['resume_edu']}'，满足JD要求。")
    print(f"📌 [第二路] ChromaDB 向量语义得分 (权重70%): {result['semantic_score']}/100")
    print(f"   说明: JD向量在 ChromaDB 数据库中与候选人经验的余弦相似度换算结果。")
    print("-" * 30)
    print(f"🚀 【最终综合推荐得分】: {result['total_score']} / 100")
    print("="*40)