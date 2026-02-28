# 🧪 OpenClaw Feishu Bot: 深度技术验收测试清单 (QA Master Checklist)

> **测试环境说明**:
> *   **核心架构**: OpenClaw (Router) + Celery (Async Task) + Milvus (Vector DB)
> *   **模型服务**: **阿里云百炼 (Bailian) Coding Plan** (用于逻辑推理/长文本/RAG) + **Qwen-VL** (用于视觉)

---

## 【P0】1. 文件权限与动态混合分析 (Dynamic Analysis & Permissions)
**核心目标**: 验证系统能否支持“即传即用”的动态文件分析，同时确保**绝对的**数据物理隔离。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **S-01** | **[核心] 私聊动态分析闭环** | 1. 销售 A 私聊上传《客户X报价单.pdf》。<br>2. 机器人回复“已阅读”。<br>3. 销售 A 提问：“这个报价的毛利是多少？” | 机器人能准确提取 PDF 中的数据并计算毛利。 | 验证 OpenClaw 是否成功调用了 `Unstructured/LlamaParse` 解析流，并将向量存入带有 `owner_id` 的分区。 |
| **S-02** | **[核心] 跨人/跨群权限隔离** | 1. 销售 A 上传上述报价单。<br>2. 销售 B 私聊机器人：“查一下客户X的报价毛利”。<br>3. 管理员在群里问：“客户X的报价”。 | 机器人对 B 和管理员均回复：“未找到相关信息”或“无权访问”。 | **关键验证**: Milvus 查询日志中，Query Filter 必须包含 `owner_id == 'user_A'` (针对A的查询) 或 `scope == 'global'` (针对其他人的查询)。 |
| **S-03** | **混合知识库检索** | 1. 用户提问：“根据《员工手册》(全局库)和刚才发的《工资单》(私有)，计算我的加班费”。 | 机器人能结合 全局规则 + 私有数据 给出准确计算结果。 | 验证 Bailian Coding Plan 模型是否接收到了两份 Context，且 OpenClaw 正确拼接了 `OR` 查询条件。 |
| **S-04** | **临时文件 TTL 清理** | 1. 上传临时文件分析。<br>2. 模拟时间流逝（或手动触发过期清理）。<br>3. 再次询问该文件内容。 | 机器人回复：“文件已过期或不存在”。 | 验证 Milvus/Redis 中对应 `file_id` 的向量是否已被物理删除。 |

---

## 【P0】2. 多模态与抗水印干扰 (Vision & Watermark)
**核心目标**: 验证百炼 VL 模型在复杂企业文档场景下的表现。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **V-01** | **强水印对抗测试** | 1. 发送一张正文被“**绝密/禁止外传**”水印高频覆盖的合同截图。<br>2. 指令：“提取合同条款文本”。 | 输出纯净条款，文字中**不包含**重复的“绝密”字样，句子通顺。 | 验证 Vision Skill 的 System Prompt 是否包含 *"Ignore background watermarks"* 指令，且 Qwen-VL 执行有效。 |
| **V-02** | **图表趋势分析** | 1. 发送一张无具体数值的销售折线图。<br>2. 提问：“哪个月份跌幅最大？” | 机器人能正确识别视觉趋势并回答月份。 | 确认 OpenClaw 调用的是百炼的 **Vision 接口** 而非简单的 OCR 工具。 |
| **V-03** | **PDF 扫描件处理** | 1. 上传一份由图片组成的扫描版 PDF (非可复制文本)。<br>2. 提问文档内容。 | 机器人能识别并回答（触发了 OCR/Vision 流程）。 | 验证当文本解析器返回空值时，是否自动 **Fallback** 到了 Vision 模式。 |

---

## 【P1】3. 多群聊同 Agent 回应与多身份 (Multi-Identity)
**核心目标**: 验证机器人在不同上下文环境中的“人设”隔离。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **I-01** | **群组人设隔离** | 1. 在“技术群”配置 Prompt 为“严谨的代码专家”。<br>2. 在“闲聊群”配置 Prompt 为“幽默小助手”。<br>3. 分别问：“Python 是什么？” | 技术群回复专业定义；闲聊群回复通俗比喻。 | 验证 OpenClaw 是否根据 `chat_id` 从 Redis 加载了不同的 System Prompt 注入给百炼模型。 |
| **I-02** | **并发会话独立性** | 1. 在群 A 和群 B 同时（毫秒级）发送消息。 | 两个群收到的回复互不串线，A 的问题不会出现在 B 的回答里。 | 验证 Celery Worker 处理任务时，Context 对象是否严格绑定了 `chat_id`。 |

---

## 【P1】4. 上下文记忆与多轮对话 (Context Retention)
**核心目标**: 验证单客户/单群组的对话连贯性。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **C-01** | **隐式指代测试** | 1. 用户：“帮我分析《财报.pdf》”。<br>2. 机器人：“已分析...”。<br>3. 用户：“那**里面的**净利润是多少？” | 机器人能识别“里面的”指代《财报.pdf》，并给出答案。 | 验证 Redis History 是否保存了上一轮的文件 Context 信息。 |
| **C-02** | **话题中断与恢复** | 1. 讨论 A 话题。<br>2. 插嘴问 B 话题（闲聊）。<br>3. 说：“回到 A 话题”。 | 机器人能接上 A 话题的思路。 | 验证 Bailian Coding Plan 的长窗口记忆能力，以及 OpenClaw 的 History 截断策略。 |
| **C-03** | **[隐形难点] 并发写冲突** | 1. 两人在同一群快速连续发言。 | 历史记录完整保留两人的发言，无覆盖丢失。 | 验证 Redis 写入 History 时是否使用了 **分布式锁 (Distributed Lock)**。 |

---

## 【P2】5. FAQ 优先路由 (FAQ Priority)
**核心目标**: 验证高频问题是否能**短路**大模型，直接返回标准答案。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **R-01** | **知识冲突仲裁** | 1. `FAQ.doc` 定义：“全勤奖=1000元”。<br>2. 上传旧文件含：“全勤奖=500元”。<br>3. 提问：“全勤奖多少？” | 机器人**秒回** 1000元，且不显示“正在分析文件”。 | 查看日志：FAQ Retriever 的 Similarity Score 应 > 0.9，触发路由熔断，**跳过** RAG 和 LLM 生成。 |
| **R-02** | **幻觉抑制** | 1. 提问一个既不在 FAQ 也不在文件里的业务问题。 | 机器人回复：“未找到相关信息，请联系人工。” **严禁编造**。 | 验证当检索 Score 低于阈值时，是否触发了 OpenClaw 的 `FallbackHandler`。 |

---

## 【P2】6. 响应延时与异步处理 (Latency & Async)
**核心目标**: 验证飞书交互体验与大文件处理的稳定性。

| ID | 测试场景 (Scenario) | 操作步骤 (Steps) | 预期结果 (Expected Result) | 技术验证点 (Technical Check) |
| :--- | :--- | :--- | :--- | :--- |
| **P-01** | **超时交互体验** | 1. 发送一个 50MB 的大 PDF（解析耗时 > 5秒）。 | 1. 飞书界面立即显示“👀 正在阅读文件...”卡片。<br>2. 解析完成后，卡片自动更新为最终答案。 | 验证 FastAPI 是否立即返回 200，且 Worker 是否正确调用了飞书的 `interactive card update` 接口。 |
| **P-02** | **重复回调幂等性** | 1. 模拟网络波动，对同一条消息触发两次飞书回调。 | 机器人**只回复一次**。 | 验证 Redis 中是否有基于 `event_id` 的去重逻辑。 |
| **P-03** | **富文本/格式解析** | 1. 发送：“@机器人 请总结 [链接] 和 **加粗文字**”。 | 机器人能剥离 `@机器人` 占位符，正确识别 Link 和格式。 | 验证 Feishu Parser 是否正确清洗了 JSON 结构。 |

---

## 7. 部署前自检清单 (Pre-flight Checklist)

*   [ ] **API Configuration**: 确认 `Bailian API Key` 配置正确，且 Coding Plan 模型配额充足。
*   [ ] **Vector Store**: 确认 Milvus 服务正常，且 Metadata (`scope`, `owner_id`) 索引已创建。
*   [ ] **Task Queue**: 确认 Redis 连接正常，Celery Worker 已启动。
*   [ ] **Permissions**: 飞书开发者后台已开通 `im:message`, `im:resource` (下载文件) 权限。
*   [ ] **Cost Control**: 已配置单文件大小限制 (如 < 20MB) 以防止 Token 消耗过大。
