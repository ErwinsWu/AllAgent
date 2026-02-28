# 🦞 OpenClaw Feishu Bot: 架构设计与技术难点深度分析

## 1. 核心架构设计 (System Architecture)

系统不再是单一的线性链条，而是基于 **"Router-Executor" (路由-执行)** 模式的分布式架构。

*   **接入层 (Gateway)**: 负责飞书协议的解包、鉴权、异步任务分发。
*   **中枢层 (OpenClaw Router)**: 负责语义意图识别，将请求分发给最合适的 Skill。
*   **技能层 (Skills)**:
    *   **Skill A (FAQ Specialist)**: 基于高频问答库的精确匹配。
    *   **Skill B (Dynamic Analyst)**: 处理动态文件上传、权限校验与深度 RAG。
    *   **Skill C (Vision Expert)**: 处理图片/PDF 的抗水印解析。
    *   **Skill D (Chit-Chat)**: 基于大模型的通用闲聊与兜底。

---

## 2. 针对 6 大核心难点的技术解决方案

### 难点 1：文件权限与混合分析 (Dynamic Permission & Hybrid Analysis)
**场景**: 知识库里有全员可见的《员工手册》，但用户 A 在私聊中发了《A的工资单》，用户 B 在群聊发了《B项目计划》。RAG 检索时必须严格隔离。

*   **技术挑战**: 如何在一个向量库中，既能查公有知识，又能查私有文件，且互不串权？
*   **解决方案**: **Metadata Filtering (元数据栅栏技术)**
    1.  **入库打标**: 向量数据库（Milvus/PGVector）的每条数据（Chunk）必须包含 `scope` 字段。
        *   **静态知识库**: `metadata={'scope': 'global', 'doc_type': 'static'}`
        *   **私聊文件**: `metadata={'scope': 'private', 'owner_id': 'user_feishu_id'}`
        *   **群聊文件**: `metadata={'scope': 'group', 'chat_id': 'group_chat_id'}`
    2.  **检索注入**: OpenClaw 在生成检索 Query 时，必须动态构建 Filter 条件：
        *   *伪代码*: `filter = (scope == 'global') OR (scope == 'private' AND owner_id == current_user) OR (scope == 'group' AND chat_id == current_chat)`
    3.  **临时索引**: 针对用户临时上传的文件，建立**会话级临时索引**，而非永久入库。

### 难点 2：多模态与抗水印干扰 (Multimodal & Watermark Resistance)
**场景**: 企业内部流转的 PDF 或截图通常带有“机密 / 禁止外传”的半透明水印。
*   **技术挑战**: 传统 OCR (如 Tesseract) 会把水印文字识别并插入到正文中，导致句子支离破碎（例如：“本月**机密**销售额为**机密**100万”）。
*   **解决方案**: **Vision LLM + Prompt Engineering**
    1.  **模型选型**: 必须使用具备原生视觉能力的大模型（如 GPT-4o, Claude 3.5 Sonnet），而非单纯的 OCR 工具。
    2.  **System Prompt 免疫**: 在 Vision Skill 中预设强指令：
        > "你是一个文档分析助手。提供的图片可能包含背景水印（如'内部资料'、'机密'）。**请完全忽略这些水印**，仅提取前景中的正文内容和表格数据。不要在输出中包含水印文字。"
    3.  **PDF 处理**:
        *   **可复制型 PDF**: 使用 `Unstructured` 或 `LlamaParse` 提取结构化文本。
        *   **扫描/图片型 PDF**: 将每页转为图片，调用 Vision Skill 处理。

### 难点 3：多群聊与多身份隔离 (Multi-Tenancy)
**场景**: 机器人同时在“技术部群”和“人事部群”。技术部在讨论代码，人事部在讨论招聘。同时，机器人可能在不同群有不同的人设（Identity）。
*   **技术挑战**: 上下文串线（Cross-Talk）以及 Agent 身份混淆。
*   **解决方案**: **Session-Scoped Memory & Configuration**
    1.  **状态路由 (State Routing)**: OpenClaw 的 Memory 模块 key 生成规则：
        *   **群聊 Key**: `session_id = {chat_id}` (全群共享记忆)。
        *   **私聊 Key**: `session_id = {user_id}`.
    2.  **动态人设**: 在 Redis 中存储每个群组的配置信息。
        *   *Group A Config*: `{"system_prompt": "你是一个严谨的代码审查员"}`
        *   *Group B Config*: `{"system_prompt": "你是一个亲切的HR助手"}`
    3.  **调用流程**: OpenClaw 收到消息 -> 读取 `chat_id` -> 从 Redis 拉取对应的人设 Prompt -> 注入 LLM 上下文。

### 难点 4：单客户上下文记忆 (Context Retention)
**场景**: 用户问：“这份文件里提到了什么？”，机器人答：“提到了A和B。”，用户追问：“那B的具体金额呢？”。
*   **技术挑战**: 机器人需要知道“B”是指上一轮回复中的B，且“文件”是指两轮前上传的文件。
*   **解决方案**: **Sliding Window + Summary (滑动窗口摘要)**
    1.  **短期记忆**: Redis List 保留最近 5-10 轮的原始对话（Raw Text），用于精确指代消解。
    2.  **文件锚点**: 当用户上传文件时，将 `file_id` 和 `file_summary` **显式写入** 当前的 System Context 中，直到会话结束或超时。
    3.  **清理机制**: 设置 Redis Key 的过期时间（如 30分钟无操作自动清除），防止内存泄漏。

### 难点 5：FAQ 优先路由 (Priority Routing)
**场景**: 用户问“发票抬头”。文件库里可能有旧合同提到旧抬头，但 `常规提问.doc` 里有新抬头。
*   **技术挑战**: RAG 的检索具有概率性，可能搜到错误的旧文件。必须确保 FAQ 的绝对权威。
*   **解决方案**: **语义路由与置信度熔断 (Semantic Routing)**
    1.  **独立索引**: 将 `常规提问.doc` 建立为独立的 FAQ 向量库。
    2.  **第一级 (FAQ Check)**: 收到 Query 后，**优先** 在 FAQ 库中搜索。
    3.  **熔断判断**:
        *   如果 Top1 相似度 Score > **0.9** (高置信度)：**直接返回预设答案**，OpenClaw 终止后续流程，不调用大模型生成，不查其他文件。
        *   如果 Score < 0.9：进入 OpenClaw，判断是去查动态文件还是闲聊。

### 难点 6：响应延时与异步处理 (Latency & Async)
**场景**: 飞书回调要求 3秒内返回，但 PDF 解析需要 15秒。
*   **技术挑战**: 超时导致飞书重试，机器人发重复消息，或直接报错。
*   **解决方案**: **Producer-Consumer (生产者-消费者模型)**
    1.  **FastAPI Gateway**:
        *   接收 Post 请求 -> 校验 -> 封装 Task -> 扔进 Redis Queue -> **立即返回 HTTP 200 OK (空包)**。
    2.  **Celery Worker**:
        *   后台消费 Queue -> 执行 OpenClaw 逻辑。
        *   **交互优化**: 收到任务后，立即调用飞书 API 发送一个 `interactive card` (卡片消息) 显示状态：“👀 正在思考...” 或 “📄 正在阅读文件...”。
        *   处理完成后，**更新 (Update)** 该卡片内容为最终答案，或者发送一条新消息。

---

## 3. 补充：潜在的隐形难点 (Hidden Challenges)

除了上述 6 点，根据工程经验，以下 4 点是极易被忽视的“大坑”：

### 难点 7：动态数据的“垃圾回收” (Data Hygiene)
*   **隐患**: 用户每天上传大量临时文件，如果全部永久存入 Milvus，一个月后检索速度变慢，且存储成本爆炸。
*   **对策**: **TTL (Time To Live) 机制**。
    *   在 Milvus/Redis 中为动态文件设置过期时间（如 24小时）。
    *   定期运行 Cron Job 清理过期向量，保持索引轻量化。

### 难点 8：飞书富文本解析 (Rich Text Parsing)
*   **隐患**: 飞书的消息是 JSON 结构，包含 `@mentions` (at人)、`images` (图片Key)、`formatting` (加粗/链接)。如果直接把 raw JSON 喂给 LLM，模型会不知所措。
*   **对策**: 编写健壮的 **Feishu Parser**。
    *   去除 `@机器人` 的占位符。
    *   提取 `image_key` 并转换为下载链接。
    *   提取纯文本用于语义分析。

### 难点 9：成本控制 (Token Economics)
*   **隐患**: 如果群里有人恶意或无意发送一本 500 页的书，或者大量高清图片，直接调用 GPT-4o 进行全量分析会瞬间烧光 API 额度。
*   **对策**:
    *   **文件大小限制**: 超过 20MB 或 50页 的文件拒绝处理。
    *   **模型分级**: 
        *   路由/闲聊 -> 使用 **GPT-4o-mini** 或 **DeepSeek** (便宜)。
        *   只有 Vision/复杂推理 -> 使用 **GPT-4o**。

### 难点 10：并发写冲突 (Concurrency Race Conditions)
*   **隐患**: 在同一个群里，用户 A 和用户 B 同时（毫秒级差）提问。两个 Worker 同时读取 Redis 里的历史记录，各自追加新回复，最后写回 Redis。**结果：其中一条历史记录被覆盖丢失**。
*   **对策**: **分布式锁 (Distributed Lock)**。
    *   在更新 Session History 时，使用 Redis Lock 锁住该 `session_id`，确保串行写入历史记录。

---

## 4. 开发路线建议

1.  **Phase 1 (基础)**: 搭建 FastAPI + Celery 异步框架，打通飞书收发消息。
2.  **Phase 2 (大脑)**: 实现 OpenClaw 路由，接入 FAQ 库，实现 **FAQ 优先熔断** 逻辑。
3.  **Phase 3 (眼睛)**: 接入 Vision 模型，调试抗水印 Prompt。
4.  **Phase 4 (记忆)**: 实现基于 Redis 的会话级记忆和 metadata 权限隔离。
5.  **Phase 5 (优化)**: 加入 TTL 清理机制和分布式锁。
