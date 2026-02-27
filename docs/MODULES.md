# 飞书AI智能体 - 模块功能详细说明

## 模块架构总览

本项目采用模块化设计，各模块职责清晰，低耦合高内聚。

```
feishu-ai-agent/
├── src/
│   ├── connector/          # 飞书连接模块
│   ├── router/             # 对话路由器
│   ├── ai_engine/          # AI对话引擎
│   ├── knowledge/          # 知识库检索模块
│   ├── product/            # 产品知识管理
│   └── utils/              # 工具函数
```

---

## 模块 1: 飞书连接模块 (Feishu Connector)

### 核心职责
作为系统与飞书平台的桥梁，处理所有飞书相关的API交互。

### 功能清单

#### 1.1 消息接收
- **功能**: 通过webhook接收飞书用户发送的消息
- **支持类型**: 文本消息、@消息、私聊消息、群聊消息
- **技术实现**: FastAPI endpoint + 事件解析

```python
# 接口示例
def receive_message(event: FeishuEvent) -> Message:
    """解析飞书消息事件"""
    return Message(
        user_id=event.sender.user_id,
        content=event.message.content,
        chat_id=event.message.chat_id
    )
```

#### 1.2 消息发送
- **功能**: 向飞书用户发送回复消息
- **支持格式**:
  - 纯文本消息
  - Markdown格式消息
  - 交互式卡片消息
- **技术实现**: lark-oapi SDK

```python
# 接口示例
def send_text_message(chat_id: str, content: str) -> bool:
    """发送文本消息到飞书"""
    pass

def send_card_message(chat_id: str, card: CardMessage) -> bool:
    """发送卡片消息到飞书"""
    pass
```

#### 1.3 事件处理
- **URL验证**: 响应飞书平台的验证请求
- **消息加解密**: 处理飞书的消息加密 (可选)
- **事件过滤**: 过滤重复事件和无关事件

#### 1.4 API封装
- **飞书文档搜索**: 调用飞书搜索API
- **文档内容获取**: 读取飞书文档内容
- **用户信息查询**: 获取用户基本信息

### 配置参数

```python
class FeishuConfig:
    app_id: str              # 应用ID
    app_secret: str          # 应用密钥
    verification_token: str  # 验证Token
    encrypt_key: str         # 加密Key (可选)
    webhook_url: str         # webhook地址
```

### 依赖项
- lark-oapi >= 1.0.0
- FastAPI >= 0.100.0

---

## 模块 2: 对话路由器 (Dialog Router)

### 核心职责
智能分析用户意图，决策最优的处理路径，避免不必要的API调用。

### 功能清单

#### 2.1 意图识别
- **功能**: 判断用户消息的意图类型
- **意图分类**:
  - `greeting`: 打招呼、闲聊
  - `product_intro`: 产品介绍请求
  - `specific_question`: 具体技术/业务问题
  - `feedback`: 反馈建议
  - `other`: 其他

```python
# 接口示例
def classify_intent(message: str) -> Intent:
    """分类用户意图"""
    # 方案1: 关键词匹配 (简单快速)
    # 方案2: LLM分类 (更准确)
    pass
```

#### 2.2 查询策略决策
- **功能**: 根据意图决定是否需要查询知识库
- **决策规则**:

```python
决策树:
├─ greeting -> 直接AI回复 (不查询)
├─ product_intro -> 使用产品知识库 (不查询飞书)
├─ specific_question -> 判断是否需要查询飞书文档
│   ├─ 包含技术关键词 -> 查询技术文档
│   ├─ 包含商务关键词 -> 查询商务文档
│   └─ 其他 -> 尝试直接回答
└─ feedback -> 记录反馈 + 礼貌回复
```

#### 2.3 上下文管理
- **功能**: 维护多轮对话的上下文
- **存储内容**:
  - 对话历史 (最近N条)
  - 用户画像
  - 当前主题

```python
class DialogContext:
    user_id: str
    history: List[Message]  # 最近5条对话
    current_topic: str      # 当前讨论主题
    last_intent: Intent     # 上一次意图
```

#### 2.4 路由执行
- **功能**: 根据决策调用相应模块
- **路由表**:

```python
ROUTE_MAP = {
    Intent.GREETING: handle_greeting,
    Intent.PRODUCT_INTRO: handle_product_intro,
    Intent.SPECIFIC_QUESTION: handle_specific_question,
}
```

### 性能优化
- 缓存常见问题的意图分类结果
- 异步调用LLM API
- 超时控制 (2秒内返回决策)

---

## 模块 3: AI对话引擎 (AI Dialog Engine)

### 核心职责
调用大语言模型，生成自然流畅的回复内容。

### 功能清单

#### 3.1 LLM调用
- **支持的模型**:
  - OpenAI GPT-4 / GPT-3.5
  - Anthropic Claude
  - 阿里通义千问
  - 自定义API接口

```python
# 统一接口设计
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Message]) -> str:
        pass

class ClaudeProvider(LLMProvider):
    def generate(self, messages: List[Message]) -> str:
        # 调用Claude API
        pass
```

#### 3.2 Prompt工程
- **系统提示词模板**:

```
你是{company_name}的AI产品顾问，名字叫{bot_name}。

你的职责:
1. 友好、专业地介绍我们的产品
2. 回答客户关于产品的问题
3. 如果不确定答案，诚实告知并引导联系人工客服

注意事项:
- 保持礼貌和耐心
- 回答要简洁明了，避免冗长
- 不要编造信息
- 适当使用表情符号增加亲和力

产品知识:
{product_knowledge}

相关文档:
{retrieved_documents}

对话历史:
{conversation_history}
```

#### 3.3 上下文注入
- **产品知识注入**: 将产品信息加入prompt
- **检索结果注入**: 将飞书文档内容加入prompt
- **对话历史注入**: 维护多轮对话连贯性

#### 3.4 回复后处理
- **内容过滤**: 敏感词过滤
- **格式优化**: Markdown格式化
- **长度控制**: 超长内容分段发送
- **引用标注**: 标注信息来源

```python
def post_process_response(raw_response: str) -> str:
    """后处理AI回复"""
    # 1. 过滤敏感词
    # 2. 格式化Markdown
    # 3. 添加来源标注
    # 4. 长度控制
    return processed_response
```

#### 3.5 流式输出 (可选)
- **功能**: 实时输出AI生成内容
- **用户体验**: 减少等待感
- **技术实现**: SSE (Server-Sent Events)

### 成本控制
- Token计数和限制
- 上下文窗口管理
- 缓存相似问题答案

---

## 模块 4: 知识库检索模块 (Knowledge Retriever)

### 核心职责
从飞书知识库中检索相关文档，为AI提供参考资料。

### 功能清单

#### 4.1 飞书文档搜索
- **功能**: 调用飞书搜索API查询文档
- **搜索范围**:
  - 飞书文档
  - 飞书Wiki
  - 飞书多维表格

```python
def search_feishu_docs(query: str, limit: int = 5) -> List[Document]:
    """搜索飞书文档"""
    # 调用飞书搜索API
    # 返回相关文档列表
    pass
```

#### 4.2 文档内容提取
- **功能**: 获取文档的完整内容
- **格式转换**: HTML -> Markdown
- **内容清洗**: 去除无关格式和元素

```python
def fetch_document_content(doc_id: str) -> str:
    """获取文档内容"""
    # 调用飞书文档API
    # 解析文档内容
    return clean_content
```

#### 4.3 相关性排序
- **方案1 (基础)**: 使用飞书API返回的排序
- **方案2 (增强)**: 基于关键词匹配度重排
- **方案3 (高级)**: 向量语义相似度排序

```python
def rerank_documents(query: str, docs: List[Document]) -> List[Document]:
    """重新排序文档"""
    # 计算相似度分数
    # 按分数排序
    return sorted_docs
```

#### 4.4 内容摘要
- **功能**: 提取文档关键信息
- **方案1**: 取文档前N个字符
- **方案2**: LLM生成摘要
- **方案3**: TextRank算法提取关键句

```python
def summarize_document(content: str, max_length: int = 500) -> str:
    """生成文档摘要"""
    # 提取关键信息
    return summary
```

#### 4.5 缓存机制
- **查询缓存**: 缓存搜索结果 (1小时)
- **文档缓存**: 缓存文档内容 (24小时)
- **更新策略**: LRU淘汰

### 性能指标
- 搜索延迟: < 1秒
- 内容提取延迟: < 2秒
- 缓存命中率: > 60%

---

## 模块 5: 产品知识管理 (Product Knowledge)

### 核心职责
存储和管理公司产品的基础信息，用于快速回答产品相关问题。

### 功能清单

#### 5.1 产品信息存储
- **数据结构**:

```json
{
  "product": {
    "name": "XX产品",
    "tagline": "产品Slogan",
    "description": "详细描述",
    "features": [
      {
        "title": "核心功能1",
        "description": "功能描述",
        "benefits": ["优势1", "优势2"]
      }
    ],
    "pricing": {
      "plans": [
        {
          "name": "基础版",
          "price": "¥999/年",
          "features": ["功能A", "功能B"]
        }
      ]
    },
    "use_cases": [
      {
        "scenario": "使用场景1",
        "solution": "解决方案"
      }
    ]
  }
}
```

#### 5.2 FAQ管理
- **常见问题库**:

```json
{
  "faqs": [
    {
      "category": "产品功能",
      "question": "产品支持哪些平台?",
      "answer": "支持Web、iOS、Android三端",
      "keywords": ["平台", "支持", "系统"]
    }
  ]
}
```

#### 5.3 知识检索
- **功能**: 根据关键词匹配FAQ
- **算法**: 关键词匹配 + 相似度计算

```python
def search_faq(query: str) -> List[FAQ]:
    """搜索FAQ"""
    # 关键词提取
    # 匹配FAQ
    # 排序返回
    pass
```

#### 5.4 知识更新
- **手动更新**: 通过配置文件
- **自动同步**: 定期从飞书文档同步
- **版本管理**: Git版本控制

#### 5.5 多语言支持 (可选)
- 中文、英文产品介绍
- 自动语言检测
- 多语言FAQ

### 数据来源
- 产品经理提供的PRD文档
- 官网产品介绍页面
- 销售部门的话术资料

---

## 模块间交互流程

### 典型对话流程

```
1. 用户发送消息到飞书
   ↓
2. [飞书连接模块] 接收消息 -> 解析
   ↓
3. [对话路由器] 分析意图 -> 决策路径
   ↓
4a. [产品知识管理] 查询FAQ (如果是基础问题)
   ↓
4b. [知识库检索] 搜索飞书文档 (如果是复杂问题)
   ↓
5. [AI对话引擎] 整合信息 -> 生成回复
   ↓
6. [飞书连接模块] 发送回复到飞书
   ↓
7. 用户收到回复
```

### 错误处理流程

```
错误发生
  ↓
记录日志
  ↓
判断错误类型
  ├─ 飞书API错误 -> 重试3次 -> 失败则返回友好提示
  ├─ LLM API错误 -> 降级到模板回复
  ├─ 超时错误 -> 返回"正在处理中"提示
  └─ 未知错误 -> 记录详情 + 通知管理员
```

---

## 扩展性设计

### 插件化架构
各模块通过接口通信,易于替换和扩展:

```python
# 知识检索接口
class KnowledgeRetriever(ABC):
    @abstractmethod
    def search(self, query: str) -> List[Document]:
        pass

# 可以轻松添加新的检索源
class WikiRetriever(KnowledgeRetriever):
    def search(self, query: str) -> List[Document]:
        # 检索内部Wiki
        pass

class DatabaseRetriever(KnowledgeRetriever):
    def search(self, query: str) -> List[Document]:
        # 检索数据库文档
        pass
```

### 配置化设计
通过配置文件控制模块行为:

```yaml
# config.yaml
router:
  intent_classifier: "llm"  # or "keyword"
  enable_context: true
  max_history: 5

ai_engine:
  provider: "claude"
  model: "claude-3-sonnet"
  temperature: 0.7
  max_tokens: 1000

knowledge:
  enable_feishu_search: true
  enable_vector_search: false
  cache_ttl: 3600
```

---

## 监控指标

### 业务指标
- 日活用户数
- 对话轮次
- 问题解决率
- 用户满意度

### 技术指标
- API响应时间
- LLM调用成功率
- 缓存命中率
- 错误率

### 成本指标
- LLM API费用
- 飞书API调用量
- 服务器资源使用

---

## 安全性考虑

### 1. 数据安全
- 用户对话数据加密存储
- 敏感信息脱敏处理
- 访问权限控制

### 2. API安全
- 飞书webhook签名验证
- LLM API密钥安全管理
- 请求频率限制

### 3. 内容安全
- 敏感词过滤
- 违规内容检测
- 人工审核机制

---

## 总结

本模块化设计遵循以下原则:
- **单一职责**: 每个模块只负责一个核心功能
- **低耦合**: 模块间通过清晰的接口通信
- **高内聚**: 相关功能集中在同一模块
- **可扩展**: 易于添加新功能和替换组件
- **可测试**: 每个模块可独立测试

通过这种设计,系统既能快速实现MVP,又能平滑升级到更复杂的版本。
