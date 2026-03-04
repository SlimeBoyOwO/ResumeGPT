# 基于大模型模型的简历审阅系统 - 个人毕设

## 一、项目简介

本项目是一个基于大模型模型的简历审阅系统，旨在帮助企业和求职者提高简历审阅的效率和准确性。系统采用大模型模型，通过训练大量简历数据，实现简历的自动审阅、推荐与打分功能。

## 二、初步设想技术栈

- 前端：Vue3，Typescript，Tailwind CSS，Pinia，Vite，pnpm管理
- 后端：Python，FastAPI，uv管理
- 数据库：MySQL，ChromaDB
- 大模型模型：WebLLM
- 辅助技术（先验证再选用）：BERT模型，Embedding，RAG，Sentence-BERT，Cross-Encoder
- 架构理念：Agent方式的MoE混合专家模型，ToT 思维树调用模型

## 三、项目功能实现情况（待技术补充和完善）

### 1. 基础前后端功能

- [x] 前端用户注册、登录、登出
- [x] 前端管理员登录、登出
- [x] 前端用户上传简历
- [x] 后端用户身份认证与前端身份记录
- [x] 管理员查看上传简历
- [ ] 网页动态查看简历内容
- [ ] 输出量化雷达图（技能、经验、学历、潜力、沟通）
- [ ] 管理员应聘与面试消息通知系统
- [ ] 应聘者查看应聘状态与面试消息通知系统

### 2. 数据存储与持久化

- [x] MySQL数据库存储简历信息
- [x] MySQL数据库存储用户信息
- [ ] MySQL数据库存储结构化LLM评分与评价信息
- [x] 前后端对数据库信息的获取与调用
- [ ] 使用 ChromaDB 进行简历信息检索与语义相似度匹配

### 3. 简历信息提取与粗精排模块（以下提及 NLP 技术将先通过 PoC 验证，如果模型能力不行或工作量大可以用 LLM 替换）

- [ ] 结构化分析简历，OCR技术或LayoutLM技术或基于BERT/BiLSTM-CRF的命名实体识别 (NER技术可选)
- [ ] 使用 MoE 混合专家模型，搭建 Router 层与 Expert 层，对简历进行粗排和精排准备。
- [ ] Router层：训练一个轻量级分类器 (DistilBERT / TextCNN) （可选，需要PoC）
- [ ] Sentence-BERT (SBERT) 或 Cross-Encoder (CE) 模型进行相似度计算粗排。推荐是前者粗排，后者替换为 LLM 精排，或结合CE先匹配分数，再使用 LLM 进行结构化评分。
- [ ] NLP 脚本，发送给大模型之前，先进行脱敏处理，使用PII技术。

### 4. 大语言模型与评分系统

- [ ] 对接 WebLLM 模型，用于简历的评分与评价
- [ ] 使用 ToT 思维树，将大模型模型的结果进行可解释的专项评分与结构化输出（使用数据库存储）
- [ ] Prompt Tunning 提示词微调，设计不同类型的Prompt，用于不同类型简历的评分与评价，以使其担当不同领域的专家
- [ ] 使用公式定义，使用 Function Tool Call 最终获取评分，带入公式并计算，存储到数据库中

## 四、项目结构

```
resume-review-system
├── frontend
│   ├── public
│   ├── src
│   ├── package.json
│   └── ...
├── backend
│   ├── app
│   │   ├── schemas
│   │   ├── routes
│   │   ├── utils
│   │   └── ...
│   ├── main.py
│   └── ...
├── scripts
│   ├── resume_generator.py
│   └── ...
├── README.md
└── ...
```

## 五、如何使用

- 后端：进入虚拟环境后`uvicorn main:app --reload`
- 前端：`pnpm run dev`

- 管理员账号：admin, admin123（实测哈希解析有问题，可以自己搞个用户之后，在数据库设定为admin）
- 用户账号：用账密在`localhost:5173`注册即可
