# 🧪 OpenClaw Feishu Bot: 深度技术验收测试清单 (QA Master Checklist)

> **测试环境说明**:
> *   **架构**: OpenClaw (Router) + Celery (Async) + Milvus (Vector DB)
> *   **模型**: 百炼Coding Plan

## 1. 核心路由与仲裁机制测试 (Router & Arbitration)
**测试目标**: 验证 OpenClaw 是否能精准分发意图，特别是在知识冲突时的优先级逻辑。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **R-01** | **FAQ 绝对霸权测试** | 1. FAQ 库定义：“全勤奖=1000元”。<br>2. 上传旧文件《2022手册.pdf》(内含“全勤奖=500元”)。<br>3. 提问：“全勤奖多少？” | 机器人坚定回答 **1000元**，并**忽略**上传的文件内容。 | 查看日志：FAQ Retriever 的 Similarity Score 应 > 0.9，触发路由熔断，**未调用** File RAG Tool。 |
| **R-02** | **闲聊/RAG 边界测试** | 1. 提问：“你觉得今天天气怎么样？”<br>2. 提问：“刚才发的文件里提到了什么天气？” | 1. 调用 General Skill 回复闲聊。<br>2. 调用 RAG Skill 检索文件。 | 验证 Router Prompt 是否能区分“通用闲聊”与“基于上下文的询问”。 |
| **R-03** | **幻觉抑制测试** | 1. 提问一个既不在 FAQ 也不在文件里的业务问题（如：“火星分部在哪？”）。 | 机器人回复：“未找到相关信息，请联系人工。” **严禁编造**。 | 验证当检索 Score 低于阈值（如 0.6）时，是否触发了 `FallbackHandler`。 |

---

## 2. 动态文件与权限隔离测试 (Dynamic RAG & Security)
**测试目标**: 基于 **Metadata Filtering** 的物理隔离验证。**此项失败则产品不可上线**。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **S-01** | **跨群组数据隔离** | 1. 在 **群组 A** 上传《项目A机密.pdf》。<br>2. 在 **群组 B** 提问：“项目A机密是什么？” | 机器人回复：“未找到相关信息”。 | 查看 Milvus 日志：Query Filter 必须包含 `chat_id == 'Group_B_ID'`。 |
| **S-02** | **私聊 vs 群聊隔离** | 1. 用户甲私聊上传《体检单.pdf》。<br>2. 用户甲在群聊（有他人在场）问：“我的体检结果？” | 机器人回复：“未找到相关信息”或“请在私聊询问”。 | 验证 Filter：群聊场景下，严禁查询 `scope='private'` 的向量数据。 |
| **S-03** | **[隐形难点] 数据TTL清理** | 1. 上传一个临时文件。<br>2. 等待设定时间（如 24h）或手动触发清理脚本。<br>3. 再次询问文件内容。 | 机器人回复：“未找到相关信息”或“文件已过期”。 | 验证 Milvus/Redis 中对应 `file_id` 的向量是否已被物理删除或标记不可见。 |

---

## 3. 视觉处理与抗水印干扰 (Vision & Watermark)
**测试目标**: 验证 Vision Skill 的 Prompt 工程与识别能力。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **V-01** | **强水印对抗** | 1. 发送一张正文被“**严禁外传**”水印覆盖的合同截图。<br>2. 要求：“提取合同条款”。 | 输出纯净条款，文字中**不包含**重复的“严禁外传”字样。 | 验证 System Prompt 中是否包含 *"Ignore background watermarks"* 指令。 |
| **V-02** | **图表数据提取** | 1. 发送一张无数值的折线趋势图。<br>2. 提问：“哪个月增长最快？” | 机器人能正确分析视觉趋势并回答月份。 | 确认调用了 GPT-4o/Claude 3.5 的 Vision 接口，而非纯 OCR。 |

---

## 4. 平台特性与边缘情况 (Platform & Edge Cases)
**测试目标**: 覆盖 **富文本解析** 与 **异步架构** 的稳定性。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **P-01** | **[隐形难点] 富文本解析** | 1. 发送消息：“@机器人 请总结 [链接] 和 **加粗文字**”。<br>2. 包含表情符号和图片。 | 机器人能剥离 `@机器人` 占位符，正确识别 Link 和纯文本。 | 验证 Feishu Parser 是否正确清洗了 JSON 结构中的 `mentions` 和 formatting。 |
| **P-02** | **3秒超时/重复回调** | 1. 发送一个 50页 的 PDF（解析 > 5秒）。<br>2. 观察飞书端表现。 | 飞书端无报错，机器人**只回复一次**最终结果。 | 1. 确认 FastAPI 立即返回 `200 OK`。<br>2. 确认 Redis 去重逻辑生效。 |
| **P-03** | **[隐形难点] 成本/Token熔断** | 1. 发送一个 500页 的 PDF 或 20MB 的高清图。<br>2. 发送一个极其复杂的 Prompt 试图诱导长输出。 | 机器人**快速拒绝**：“文件过大”或“请求超出限制”。 | 验证文件预检逻辑（Size Check）是否在调用 LLM 之前拦截。 |

---

## 5. 并发与状态一致性 (Concurrency & Consistency)
**测试目标**: 验证 **竞态条件 (Race Conditions)** 与上下文记忆。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **C-01** | **[隐形难点] 并发写冲突** | 1. 两个用户在同一群组内，**毫秒级同时**发送不同消息。<br>2. 观察机器人的回复和后续记忆。 | 机器人分别回复两人，且两人的话都被计入 History，**无覆盖丢失**。 | 验证 Redis 写入 History 时是否使用了 **分布式锁 (Distributed Lock)**。 |
| **C-02** | **话题中断与恢复** | 1. 用户：“文件里A预算多少？”<br>2. 插嘴：“今天是星期几？”<br>3. 用户：“回到刚才预算问题”。 | 机器人能接上之前的思路，回答预算。 | 验证 Memory 是否保存了完整 History，且 LLM 具备指代消解能力。 |
| **C-03** | **多身份配置** | 1. 在群 A 配置“严谨助手”，群 B 配置“幽默助手”。<br>2. 分别问同一个问题。 | 群 A 回复正式，群 B 回复活泼。 | 验证 OpenClaw 是否根据 `chat_id` 动态加载了不同的 System Prompt。 |

---

## 6. 部署前自检清单 (Pre-flight Checklist)

*   [ ] **Vector Store**: 确认 Milvus/PGVector 服务正常，**Metadata 索引已创建**。
*   [ ] **Task Queue**: 确认 Redis 连接正常，Celery Worker 处于活跃状态。
*   [ ] **Clean Up**: 确认已配置定期清理过期向量的 Cron Job (针对隐形难点 #1)。
*   [ ] **Permissions**: 飞书后台已开通 `im:message`, `im:resource` (下载文件) 权限。
*   [ ] **Cost Monitor**: 已设置 OpenAI/LLM API 的每日额度告警 (针对隐形难点 #3)。
