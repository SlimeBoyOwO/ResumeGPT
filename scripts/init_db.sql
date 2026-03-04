-- ResumeGPT 数据库初始化脚本
-- MySQL 连接：localhost:3306, root/password

CREATE DATABASE IF NOT EXISTS resume_gpt
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE resume_gpt;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    email       VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'user' COMMENT '角色: user / admin',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 简历表
CREATE TABLE IF NOT EXISTS resumes (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT          NOT NULL,
    filename            VARCHAR(255) NOT NULL COMMENT '存储文件名(UUID)',
    original_filename   VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path           VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_size           BIGINT       NOT NULL COMMENT '文件大小(bytes)',
    file_type           VARCHAR(20)  NOT NULL COMMENT '文件类型(pdf/docx/jpg等)',
    status              VARCHAR(20)  NOT NULL DEFAULT 'pending' COMMENT '处理状态: pending/processing/completed/failed',
    score               FLOAT        NULL     COMMENT '简历综合评分',
    analysis_summary    TEXT         NULL     COMMENT '分析摘要',
    best_match_position VARCHAR(200) NULL     COMMENT '最佳匹配岗位',
    uploaded_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员账号 (密码: admin123, bcrypt hash)
-- 注意：此 hash 由 passlib bcrypt 生成，对应密码 "admin123"
-- 如需修改密码，可通过后端 API 或重新生成 hash
INSERT IGNORE INTO users (username, email, hashed_password, role)
VALUES ('admin', 'admin@resumegpt.com', '$2b$12$LJ3m4ys3Lk0TSwHjgNqPduQXooiMmRBfOGF1r/jEul0d43kJoJFHa', 'admin');
