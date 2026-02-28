# 🦞 OpenClaw Feishu Bot: 架构设计与技术难点深度分析

## 1. 核心架构设计 (System Architecture)

系统基于 **OpenClaw (Router)** + **百炼 Coding Plan (LLM Backend)** 的双脑架构。

*   **Brain (OpenClaw Router)**: 负责接收飞书消息，进行语义意图识别，将任务分发给具体的 Skill。
*   **Model Layer**: 统一接入 **阿里云百炼 (Bailian) Coding Plan** 模型服务，利用其强大的指令遵循和长文本能力。
*   **Skills (技能层)**:
    *   **Skill A (Dynamic Analyst)**: **[P0 核心]** 处理用户实时上传的文件（PDF/图片）及静态知识库，支持严格的权限隔离。
    *   **Skill B (Vision Expert)**: **[P0 核心]** 处理带水印的图片/PDF 解析。
    *   **Skill C (Multi-Identity)**: **[P1 重要]** 支持多群组、多身份的独立响应。
    *   **Skill D (Context Keeper)**: **[P1 重要]** 维护单人/单群的上下文记忆。
    *   **Skill E (FAQ Specialist)**: **[P2 常规]** 基于高频问答库的精确匹配。

---

## 2. 核心难点与技术方案 (按优先级排序)

### 【P0 - 最高优先级】难点 1：文件权限与动态混合分析 (Dynamic Permission & Analysis)
**用户故事 (User Story)**:
> *   **场景 A (私聊分析)**: 销售小王在私聊中发给机器人一份《客户A报价单.pdf》，并问：“这个报价利润率是多少？”。机器人能立即阅读并回答。**关键点**：其他同事（包括管理员）在群里问“客户A报价多少”，机器人必须回答“不知道”。
> *   **场景 B (群聊协同)**: 项目经理在“项目交付群”上传了《验收标准_v3.pdf》。群里所有成员都可以@机器人问：“验收标准里关于测试的部分怎么说？”。**关键点**：该文件仅限本群成员查询，其他群无法访问。
> *   **场景 C (全员知识)**: 任何员工都可以问“公司发票抬头是什么”，机器人基于预设的《员工手册》回答。

**技术方案：Metadata Filtering (元数据栅栏技术)**
1.  **动态入库打标**: 向量数据库（Milvus/PGVector）的每条 Chunk 必须包含 `scope` 字段。
    *   **静态知识库**: `metadata={'scope': 'global', 'doc_type': 'static'}`
    *   **私聊文件**: `metadata={'scope': 'private', 'owner_id': 'user_feishu_id'}`
    *   **群聊文件**: `metadata={'scope': 'group', 'chat_id': 'group_chat_id'}`
2.  **检索注入 (Query Injection)**: OpenClaw 在生成检索 Query 时，必须动态构建 Filter 条件：
    *   *Code Logic*: `filter = (scope == 'global') OR (scope == 'private' AND owner_id == current_user) OR (scope == 'group' AND chat_id == current_chat)`
3.  **临时索引生命周期**: 针对用户临时上传的文件，建立**会话级临时索引**。设置 TTL (如 24小时)，过期自动清理，防止隐私数据残留。

---

### 【P0 - 最高优先级】难点 2：多模态与抗水印干扰 (Multimodal & Watermark)
**用户故事**:
> 员工发了一张带有密集“机密 / 禁止外传”水印的合同截图，或者一份扫描版 PDF。机器人需要提取合同金额，且不能把水印文字当成合同内容。

**技术方案：Vision-Native + Prompt Engineering**
1.  **模型调用**: 调用 **百炼 (Qwen-VL/Omni)** 的视觉能力接口。
2.  **System Prompt 免疫**:
    > "你是一个文档分析助手。图片中包含背景水印（如'机密'、'禁止外传'）。**请完全忽略这些水印**，仅提取前景中的正文内容和表格数据。不要在输出中包含水印文字。"
3.  **PDF 处理策略**:
    *   **可复制型 PDF**: 使用 `Unstructured` 或 `LlamaParse` 提取结构化文本（保留表格 Markdown 格式）。
    *   **扫描/图片型 PDF**: 将每页转为图片，调用 Vision Skill 处理。

---

### 【P1 - 重要】难点 3：多群聊同 Agent 回应或多身份 Agent (Multi-Identity)
**用户故事**:
> 同一个机器人在“技术群”里是严肃的代码助手，在“行政群”里是活泼的小助手。且两个群的对话互不干扰。

**技术方案：Session-Scoped Config**
1.  **配置隔离**: 在 Redis 中存储每个群组的配置信息。
    *   *Group A Config*: `{"system_prompt": "你是一个严谨的代码审查员", "temperature": 0.1}`
    *   *Group B Config*: `{"system_prompt": "你是一个亲切的行政助手", "temperature": 0.7}`
2.  **动态加载**: OpenClaw 收到消息 -> 读取 `chat_id` -> 从 Redis 拉取对应的人设 Prompt -> 注入百炼模型的 System Context。

---

### 【P1 - 重要】难点 4：上下文记忆 (Context Retention)
**用户故事**:
> 用户：“这份文件里提到了A项目吗？” -> 机器人：“提到了。” -> 用户：“那A项目的预算是多少？” -> 机器人需知道“A项目”指代上一轮的内容。

**技术方案：Sliding Window + Summary**
1.  **短期记忆**: Redis List 保留最近 5-10 轮的原始对话（Raw Text），用于精确指代消解。
2.  **文件锚点**: 当用户上传文件时，将 `file_id` 和 `file_summary` **显式写入** 当前的 System Context 中，直到会话结束。
3.  **清理机制**: 设置 Redis Key 的过期时间（如 30分钟无操作自动清除），防止内存泄漏。

---

### 【P2 - 常规】难点 5：FAQ 优先路由 (Priority Routing)
**用户故事**:
> 用户问“发票抬头”。RAG 可能会在旧合同里搜到旧抬头。机器人必须优先回答 `常规提问.doc` 里的新抬头。

**技术方案：语义路由与置信度熔断**
1.  **独立索引**: 将 `常规提问.doc` 建立为独立的 FAQ 向量库。
2.  **第一级 (FAQ Check)**: 收到 Query 后，**优先** 在 FAQ 库中搜索。
3.  **熔断判断**:
    *   如果 Top1 相似度 Score > **0.9** (高置信度)：**直接返回预设答案**，OpenClaw 终止后续流程，不调用大模型生成。
    *   如果 Score < 0.9：进入 OpenClaw，判断是去查动态文件还是闲聊。

---

### 【P2 - 常规】难点 6：响应延时及异步处理 (Latency & Async)
**用户故事**:
> 用户上传 50 页 PDF。机器人不能“死机”不回消息，也不能因为飞书超时重试而发两遍“正在分析”。

**技术方案：Producer-Consumer 模式**
1.  **FastAPI Gateway**:
    *   接收 Post 请求 -> 校验 -> 封装 Task -> 扔进 Redis Queue -> **立即返回 HTTP 200 OK (空包)**。
2.  **Celery Worker**:
    *   后台消费 Queue -> 执行 OpenClaw 逻辑。
    *   **交互优化**: 收到任务后，立即调用飞书 API 发送一个 `interactive card` (卡片消息) 显示状态：“👀 正在阅读文件...”。
    *   处理完成后，**更新 (Update)** 该卡片内容为最终答案。

---

## 3. 补充：潜在的隐形难点 (Hidden Challenges)

### 难点 7：动态数据的“垃圾回收” (Data Hygiene)
*   **隐患**: 用户每天上传大量临时文件，如果全部永久存入 Milvus，检索速度变慢且成本爆炸。
*   **对策**: **TTL (Time To Live) 机制**。在 Milvus 中为动态文件设置过期时间（如 24小时），定期清理。

### 难点 8：飞书富文本解析 (Rich Text Parsing)
*   **隐患**: 飞书消息包含 `@mentions`、`images` key、formatting。直接喂给模型会造成干扰。
*   **对策**: 编写健壮的 **Feishu Parser**，提取纯文本和图片链接。

### 难点 9：百炼模型的 Token 成本控制
*   **隐患**: 群聊中大量无关闲聊或大文件分析消耗 Token。
*   **对策**: **文件大小限制** (如 < 20MB) + **模型分级** (简单闲聊使用更便宜的模型版本，复杂分析使用 Qwen-Max)。

### 难点 10：并发写冲突 (Concurrency Race Conditions)
*   **隐患**: 同一群组多人同时提问，导致历史记录覆盖。
*   **对策**: **Redis 分布式锁**，确保 Session History 串行写入。
