# 多渠道AI智能体 - 核心模块功能

## 1. 渠道接入模块 (Channel Connector)

**职责**: 作为统一网关，处理与各个前端渠道（飞书、钉钉、Web UI 等）的交互与协议转换。

**核心功能**:
- 统一接收多渠道的消息事件 (Webhook / WebSocket)
- 抹平平台差异，将各平台特定消息格式转换为内部标准消息对象
- 将 AI 生成的回复转换为目标平台支持的格式（文本、富文本卡片等）并发送
- 处理各平台的鉴权、加解密及 URL 验证

**技术实现**:
```python
# FastAPI 多渠道 Webhook 路由示例
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook/feishu")
async def handle_feishu_event(request: Request):
    # 解析飞书协议 -> 转换内部标准格式 -> 触发后续逻辑
    pass

@router.post("/webhook/dingtalk")
async def handle_dingtalk_event(request: Request):
    # 解析钉钉协议 -> 转换内部标准格式 -> 触发后续逻辑
    pass

@router.post("/api/chat")
async def handle_web_ui_message(request: Request):
    # 处理自建 Web 前端/App 传来的标准 JSON 请求
    pass
```

## 2. 对话路由器 (Dialog Router)

**职责**: 智能大脑的“交通调度员”，判断如何最精准、高效地处理用户问题。

**核心功能**:
- 意图识别与分类 (产品介绍 / 技术排障 / 商务咨询 / 闲聊)
- 决策查询策略（判断是否需要调用外部工具或检索企业文档）
- 路由到相应的处理管道或 Agent 节点

**决策逻辑**:
```text
标准化用户消息 -> 意图与实体分析 -> {
  基础产品咨询: 直接读取轻量级【产品知识管理模块】
  深度技术/业务问题: 触发【知识库检索模块】查询企业文档
  复杂任务(如提交流程): 触发 API 调用工具(Function Calling)
  闲聊/兜底: 直接由【AI对话引擎】生成安抚或引导回复
}
```

## 3. AI对话引擎 (AI Dialog Engine)

**职责**: 系统的核心思考与表达中枢，生成自然语言回复。

**核心功能**:
- 调用底层 LLM API (支持 OpenAI, Claude, 或私有化部署的国产大模型)
- 会话上下文管理 (Memory 管理，控制 Token 长度)
- 组装 Prompt：注入系统人设、路由分发的知识片段及搜索结果
- 保证输出的合规性与友好度

**Prompt工程**:
```text
系统提示词(System Prompt):
- 你是XX公司的首席智能顾问
- 请基于下方提供的【参考知识】来回答用户问题
- 如果【参考知识】中没有相关信息，请诚实说明，并引导客户咨询人工客服，切勿编造

历史上下文: {History_Context}
参考知识: {Retrieved_Knowledge}
当前用户问题: {User_Query}
```

## 4. 知识库检索模块 (Knowledge Retriever)

**职责**: 智能体的“外部记忆”，从企业各数据源中提取相关背景知识。

**核心功能**:
- 接入多源异构数据（企业Wiki、飞书/钉钉云文档、本地PDF、官网爬虫等）
- 文本预处理与分块 (Chunking)
- 向量化处理 (Embedding) 与混合检索 (语义检索 + 关键词检索)
- 召回内容的重排序 (Reranking) 与摘要提取

**实现方案**:
- **API直连版**: 针对支持搜索的平台（如飞书文档搜索 API），直接透传关键词获取结果。
- **RAG标准版**: 建立独立的向量数据库（如 ChromaDB, Milvus），预先将各渠道文档索引化，实现跨平台的企业级搜索。

## 5. 产品知识管理 (Product Knowledge)

**职责**: 存储和管理结构化、高频更新的基础产品信息，作为一种快速响应的高速缓存区。

**核心功能**:
- 维护核心产品词典与基础介绍
- 管理高频常见问题 (Hot FAQ)
- 提供给【对话路由器】进行快速匹配，减少不必要的重度文档检索(LLM调用)，降低延迟与成本

**数据格式**:
```json
{
  "product_id": "PROD-001",
  "product_name": "XX企业版",
  "description": "面向大中型企业的全场景解决方案...",
  "key_features": ["特性A", "特性B", "特性C"],
  "pricing_tier": "需联系销售评估",
  "hot_faqs": [
    {"question": "支持私有化部署吗？", "answer": "支持，请联系商务提供您的服务器规模信息。"}
  ]
}
```
