CREATE DATABASE IF NOT EXISTS resume_gpt
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE resume_gpt;

-- 1. 用户表 (区分企业HR和普通求职者)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'user' COMMENT '角色: user / admin',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 简历表 (新增NER提取结果和向量数据库映射)
CREATE TABLE IF NOT EXISTS resumes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL COMMENT '存储文件名(UUID)',
    original_filename VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_type VARCHAR(20) NOT NULL COMMENT '文件类型(pdf/docx等)',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '解析状态: pending/parsing/parsed/failed',
    ner_extracted_data JSON NULL COMMENT 'NER模型提取的关键信息(结构化JSON，如技能、学历、年限)',
    vector_id VARCHAR(100) NULL COMMENT '对应向量数据库中的ID',
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 岗位 JD 表
CREATE TABLE IF NOT EXISTS job_descriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    enterprise_id INT NOT NULL COMMENT '发布JD的企业用户ID',
    title VARCHAR(100) NOT NULL COMMENT '岗位名称',
    department VARCHAR(100) NULL COMMENT '所属部门',
    description TEXT NOT NULL COMMENT '岗位描述与要求摘要',
    vector_id VARCHAR(100) NULL COMMENT 'JD在向量数据库中的ID，用于粗匹配',
    status VARCHAR(20) NOT NULL DEFAULT 'open' COMMENT '状态: open/closed',
    workflow_graph JSON NULL COMMENT '图节点工作流(包含nodes和edges)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enterprise_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_enterprise (enterprise_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 专家 / Agent 设定表
CREATE TABLE IF NOT EXISTS experts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL COMMENT '专家名称(如: Java技术专家, HR政委)',
    description VARCHAR(255) NULL COMMENT '专家侧重领域的描述',
    system_prompt TEXT NOT NULL COMMENT '该专家专属的 System Prompt',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 6. 核心：匹配记录表 (简历投递 & 评估全生命周期)
CREATE TABLE IF NOT EXISTS match_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jd_id INT NOT NULL,
    resume_id INT NOT NULL,
    workflow_status VARCHAR(30) NOT NULL DEFAULT 'rough_matching' COMMENT '状态: rough_matching(粗排中) / agent_evaluating(专家评估中) / completed(完成) / failed',
    vector_similarity FLOAT NULL COMMENT '向量粗匹配的语义相似度得分',
    final_score FLOAT NULL COMMENT '多专家加权计算后的最终总分',
    comprehensive_summary TEXT NULL COMMENT '最终由综合专家(C专家)给出的整体总结报告',
    ability_summary JSON NULL COMMENT '用于显示雷达图的json能力总结',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_jd_resume (jd_id, resume_id), -- 防止同一份简历重复投递/匹配同一个JD
    FOREIGN KEY (jd_id) REFERENCES job_descriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 专家评估明细表 (记录每个Agent的输出)
CREATE TABLE IF NOT EXISTS expert_evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_record_id INT NOT NULL,
    node_id VARCHAR(50) NOT NULL COMMENT '图工作流中的节点ID',
    expert_id INT NOT NULL COMMENT '关联的专家模板ID',
    agent_status VARCHAR(20) NOT NULL DEFAULT 'processing' COMMENT '单个Agent状态: processing / success / failed',
    score FLOAT NULL COMMENT '该专家给出的单项原始评分 (例如0-100分)',
    analysis_content TEXT NULL COMMENT '该专家输出的详细点评与分析理由',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_record_id) REFERENCES match_records(id) ON DELETE CASCADE,
    FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE CASCADE,
    UNIQUE KEY uk_match_expert_node (match_record_id, node_id) -- 一次匹配中，一个节点只出具一份报告
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;